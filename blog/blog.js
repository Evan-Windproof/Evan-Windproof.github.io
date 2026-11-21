'use strict';
let settings={};try{settings=JSON.parse(localStorage.getItem('evavind-settings')||'{}')}catch{}
function theme(){document.body.classList.toggle('light',settings.theme==='light')}
function save(){try{localStorage.setItem('evavind-settings',JSON.stringify(settings))}catch{}}
theme();I18n.setLanguage(I18n.language);
const language=document.querySelector('#blog-language');language.value=I18n.language;
language.addEventListener('change',()=>{settings.language=language.value;save();I18n.setLanguage(language.value)});
document.querySelector('#blog-theme').addEventListener('click',()=>{settings.theme=settings.theme==='light'?'dark':'light';save();theme()});
const search=document.querySelector('#blog-search');search?.addEventListener('input',()=>{let count=0;document.querySelectorAll('[data-search]').forEach(el=>{el.hidden=!el.dataset.search.toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase());if(!el.hidden)count++});document.querySelector('#search-empty').hidden=count>0});
