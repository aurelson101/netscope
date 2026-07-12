import {expect,test} from '@playwright/test';
test('connexion et affichage du tableau de bord',async({page})=>{
  await page.route('**/api/v1/auth/login',route=>route.fulfill({json:{access_token:'test-token',token_type:'bearer',user:{username:'admin',role:'admin'}}}));
  await page.route('**/api/v1/dashboard',route=>route.fulfill({json:{total:2,online:1,offline:0,unknown:1,new_24h:1,by_vendor:[],by_type:[],by_os:[],recent_scans:[]}}));
  await page.goto('/');await page.getByLabel(/nom d’utilisateur/i).fill('admin');await page.getByLabel(/mot de passe/i).fill('Password123!');await page.getByRole('button',{name:/se connecter/i}).click();
  await expect(page.getByText('Tableau de bord',{exact:true}).first()).toBeVisible();
});
