import {FormEvent,useEffect,useState} from 'react';
import {Shield,UserPlus} from 'lucide-react';
import {api} from '../lib/api';
import {Layout} from '../components/Layout';

export function Users(){
  const [users,setUsers]=useState<any[]>([]),[message,setMessage]=useState('');
  const load=()=>api<any[]>('/users').then(setUsers).catch(e=>setMessage(e.message));
  useEffect(()=>{void load()},[]);
  async function create(e:FormEvent<HTMLFormElement>){e.preventDefault();const f=new FormData(e.currentTarget);try{await api('/users',{method:'POST',body:JSON.stringify({username:f.get('username'),password:f.get('password'),role:f.get('role')})});e.currentTarget.reset();load()}catch(x:any){setMessage(x.message)}}
  async function update(user:any,values:any){try{await api('/users/'+user.id,{method:'PATCH',body:JSON.stringify(values)});load()}catch(x:any){setMessage(x.message)}}
  async function revoke(user:any){await api(`/users/${user.id}/sessions`,{method:'DELETE'});setMessage(`Sessions de ${user.username} révoquées`)}
  return <Layout title="Utilisateurs et rôles"><div className="split"><article className="panel formPanel"><h3><UserPlus/>Créer un utilisateur</h3><form onSubmit={create}><label>Identifiant<input name="username" required minLength={3}/></label><label>Mot de passe initial<input name="password" type="password" minLength={12} required/></label><label>Rôle<select name="role"><option value="viewer">Lecteur</option><option value="operator">Opérateur</option><option value="admin">Administrateur</option></select></label><button className="primary">Créer</button></form>{message&&<div className="hint">{message}</div>}</article><article className="panel tablePanel"><table><thead><tr><th>Compte</th><th>Rôle</th><th>État</th><th>Sessions</th></tr></thead><tbody>{users.map(u=><tr key={u.id}><td><b>{u.username}</b></td><td><select value={u.role} onChange={e=>update(u,{role:e.target.value})}><option value="viewer">Lecteur</option><option value="operator">Opérateur</option><option value="admin">Administrateur</option></select></td><td><button onClick={()=>update(u,{active:!u.active})} className={u.active?'button':'danger'}>{u.active?'Actif':'Inactif'}</button></td><td><button onClick={()=>revoke(u)}><Shield/> Révoquer</button></td></tr>)}</tbody></table></article></div></Layout>
}
