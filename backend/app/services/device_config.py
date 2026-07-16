import asyncio,hashlib,re,tempfile
from pathlib import Path
import asyncssh

PLATFORMS={
    "cisco_ios":{"backup":"show running-config","remote":"/flash/netscope-restore.cfg","restore":"configure replace flash:netscope-restore.cfg force"},
    "eos":{"backup":"show running-config","remote":"/mnt/flash/netscope-restore.cfg","restore":"configure replace flash:netscope-restore.cfg"},
    "junos":{"backup":"show configuration | display set | no-more","remote":"/var/tmp/netscope-restore.conf","restore":"cli -c 'configure exclusive; load override /var/tmp/netscope-restore.conf; commit and-quit'"},
    "fortios":{"backup":"show full-configuration","remote":None,"restore":None},
}
ANSI=re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

def platform_policy(platform:str)->dict:
    if platform not in PLATFORMS:raise ValueError("Plateforme réseau non prise en charge")
    return PLATFORMS[platform]

def validate_ssh_secret(secret:dict)->None:
    if bool(secret.get("password"))==bool(secret.get("private_key")):raise ValueError("Fournissez soit un mot de passe, soit une clé privée SSH")
    try:asyncssh.import_public_key(secret.get("host_key","").strip())
    except (KeyError,ValueError,asyncssh.KeyImportError) as exc:raise ValueError("Clé hôte SSH OpenSSH invalide") from exc
    if secret.get("private_key"):
        try:asyncssh.import_private_key(secret["private_key"],passphrase=secret.get("passphrase"))
        except (ValueError,asyncssh.KeyImportError) as exc:raise ValueError("Clé privée SSH ou phrase secrète invalide") from exc

def config_checksum(content:str)->str:return hashlib.sha256(content.encode()).hexdigest()

def validate_configuration(content:str)->str:
    cleaned=ANSI.sub("",content).replace("\r","").strip()
    if len(cleaned)<20:raise ValueError("La configuration reçue est vide ou incomplète")
    if len(cleaned.encode())>10*1024*1024:raise ValueError("La configuration dépasse 10 Mo")
    return cleaned+"\n"

async def _connect(host:str,secret:dict):
    validate_ssh_secret(secret);host_key=secret.get("host_key","").strip()
    port=int(secret.get("port",22));known_name=host if port==22 else f"[{host}]:{port}"
    known=tempfile.NamedTemporaryFile("w",delete=False,encoding="utf-8");known.write(f"{known_name} {host_key}\n");known.close()
    keys=[]
    try:
        if secret.get("private_key"):keys=[asyncssh.import_private_key(secret["private_key"],passphrase=secret.get("passphrase"))]
        connection=await asyncio.wait_for(asyncssh.connect(host,port=port,username=secret["username"],password=secret.get("password"),client_keys=keys or None,known_hosts=known.name,login_timeout=15),timeout=20)
        return connection,known.name
    except Exception:
        Path(known.name).unlink(missing_ok=True);raise

async def capture_configuration(host:str,secret:dict,platform:str)->str:
    policy=platform_policy(platform);connection,known_path=await _connect(host,secret)
    try:
        result=await asyncio.wait_for(connection.run(policy["backup"],check=True,timeout=60),timeout=70)
        return validate_configuration(result.stdout)
    finally:connection.close();await connection.wait_closed();Path(known_path).unlink(missing_ok=True)

async def restore_configuration(host:str,secret:dict,platform:str,content:str)->None:
    policy=platform_policy(platform)
    if not policy["restore"]:raise ValueError("La restauration automatique n'est pas prise en charge sur cette plateforme")
    content=validate_configuration(content);connection,known_path=await _connect(host,secret)
    try:
        async with connection.start_sftp_client() as sftp:
            async with sftp.open(policy["remote"],"w") as remote:await remote.write(content)
        await asyncio.wait_for(connection.run(policy["restore"],check=True,timeout=180),timeout=190)
    finally:connection.close();await connection.wait_closed();Path(known_path).unlink(missing_ok=True)
