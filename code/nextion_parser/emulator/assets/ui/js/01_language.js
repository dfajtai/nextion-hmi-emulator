// ---------- language ----------
(function(){
  const q=new URLSearchParams(location.search).get('lang');
  setLang(I18N[q]?q:(I18N[lsGet('nx_lang')]?lsGet('nx_lang'):(DATA.lang||'hu')));
})();
function applyStatic(){   // static texts from the data-i* attributes
  document.querySelectorAll('[data-i]').forEach(e=>{e.textContent=t(e.dataset.i);});
  document.querySelectorAll('[data-ih]').forEach(e=>{e.innerHTML=t(e.dataset.ih);});
  document.querySelectorAll('[data-it]').forEach(e=>{e.title=t(e.dataset.it);});
  document.querySelectorAll('[data-ip]').forEach(e=>{e.placeholder=t(e.dataset.ip,DATA.examples);});   // {page}/{ref} in the texts: real names from this project
  document.documentElement.lang=LANG;
  document.title=t('app.title',{project:PROJECT});$('apptitle').textContent=document.title;
  $('helplink').href='help.html?lang='+LANG;
  $('lang').value=LANG;
  document.querySelectorAll('.card>h2').forEach(h=>{h.title=t('card.toggle');});
}
