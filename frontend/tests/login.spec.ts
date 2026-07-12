import {expect,test} from '@playwright/test';

test('connexion et affichage du tableau de bord',async({page})=>{
  await page.route('**/api/v1/auth/login',route=>route.fulfill({json:{access_token:'test-token',token_type:'bearer',user:{username:'admin',role:'admin'}}}));
  await page.route('**/api/v1/dashboard',route=>route.fulfill({json:{total:5,online:3,offline:1,unknown:1,new_24h:1,by_vendor:[{label:'Cisco',value:3}],by_type:[{label:'switch',value:3},{label:'server',value:2}],by_os:[{label:'Linux',value:2}],recent_scans:[]}}));
  await page.goto('/');
  await page.getByLabel(/nom d’utilisateur/i).fill('admin');
  await page.getByLabel(/mot de passe/i).fill('Password123!');
  await page.getByRole('button',{name:/se connecter/i}).click();
  await expect(page.getByText('Tableau de bord',{exact:true}).first()).toBeVisible();
  await expect(page.locator('.donutTotal')).toContainText('5');
  await expect(page.locator('.recharts-pie-sector')).toHaveCount(2);
  const exportButton=page.getByRole('button',{name:'Exporter'});
  await expect(exportButton).toHaveCSS('min-height','38px');
  await expect(exportButton).toHaveCSS('border-radius','7px');
});
