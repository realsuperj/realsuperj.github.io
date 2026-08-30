---
# the default layout is 'page'
icon: fas fa-toolbox
order: 4
---

<style>
/* 整张卡片是唯一入口。卡内不再放任何独立链接 —— 图、标题、按钮三个入口
   指向同一个地方，读者要先判断点哪个，反而是负担。 */
.skill-card{
  display:flex;gap:22px;align-items:center;
  padding:18px 22px;margin:20px 0;
  border:1px solid var(--main-border-color,#e9ecef) !important;
  border-radius:12px;
  text-decoration:none !important;
  color:inherit !important;
  transition:border-color .18s,transform .18s,box-shadow .18s;
}
.skill-card:hover{
  border-color:var(--link-color) !important;
  transform:translateY(-2px);
  box-shadow:0 6px 20px rgba(0,0,0,.13);
}
/* 海报走背景图而不是 <img>：Chirpy 会自动给正文里的 img 套一层
   <a class="img-link"> 做灯箱，套在卡片链接里就成了嵌套 <a>，
   浏览器会把外层链接提前闭合，属性直接漏成页面上的文字。 */
.skill-poster{
  flex:0 0 128px;width:128px;aspect-ratio:2/3;
  background-size:cover;background-position:center top;
  border-radius:8px;border:1px solid var(--main-border-color,#e9ecef);
}
.skill-body{flex:1;min-width:0}
.skill-body h3{margin:0 0 8px;font-size:1.18rem;line-height:1.35;transition:color .18s}
.skill-card:hover .skill-body h3{color:var(--link-color)}
.skill-body p{margin:0 0 10px;font-size:.92rem;line-height:1.7;color:var(--text-muted-color,#6c757d)}
.skill-tag{
  font-size:.76rem;letter-spacing:.02em;
  color:var(--text-muted-color,#6c757d);opacity:.7;
}
.skill-arrow{
  flex:0 0 auto;font-size:1.35rem;line-height:1;
  color:var(--text-muted-color,#6c757d);opacity:.35;
  transition:opacity .18s,transform .18s,color .18s;
}
.skill-card:hover .skill-arrow{opacity:1;transform:translateX(4px);color:var(--link-color)}
@media(max-width:640px){
  .skill-card{flex-direction:column;align-items:center;gap:16px;padding:18px}
  .skill-poster{flex:none;width:200px}
  .skill-arrow{display:none}
}
</style>

欢迎参观我的 AI 百宝箱～ 🧰

总有些事反复折腾我，索性写成 skill 交给 AI 去干，自己用顺手了才放到这儿。

擅长什么、不碰什么都写在里面，合用就带走 👇

全部采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh) 授权：可自由传播和修改，请保留署名，勿用于商业用途。

<!-- entries -->
<a class="skill-card" href="/pages/skill-library-curator/">
  <span class="skill-poster" style="background-image:url('/pages/skill-library-curator/poster.png')"></span>
  <div class="skill-body">
    <h3>Skill 收藏整理器</h3>
    <p>把一整个文件夹的 skill 收藏，整理成分好类、编好号、评过分、去过重的一份清单。</p>
    <span class="skill-tag">CC BY-NC 4.0 · 36 KB</span>
  </div>
  <span class="skill-arrow">→</span>
</a>
