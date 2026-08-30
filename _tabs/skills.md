---
# the default layout is 'page'
icon: fas fa-toolbox
order: 4
---

<style>
.skill-card{
  display:flex;gap:20px;align-items:flex-start;
  padding:20px;margin:22px 0;
  border:1px solid var(--main-border-color,#e9ecef);border-radius:10px;
  transition:.2s;
}
.skill-card:hover{box-shadow:0 4px 18px rgba(0,0,0,.08)}
.skill-card > a{flex:0 0 150px}
.skill-card img{
  width:150px;border-radius:6px;display:block;
  border:1px solid var(--main-border-color,#e9ecef);
}
.skill-meta{flex:1;min-width:0}
.skill-meta h3{margin:2px 0 8px;font-size:1.2rem}
/* Chirpy 的全局 a 样式优先级更高，这里必须提权才压得住下划线 */
.skill-card a,
.skill-card a:hover{text-decoration:none !important}
.skill-meta h3 a{color:var(--heading-color,inherit)}
.skill-meta h3 a:hover{color:var(--link-color)}
.skill-meta p{margin:0 0 14px;font-size:.92rem;line-height:1.7;color:var(--text-muted-color,#6c757d)}
.skill-go{font-size:.88rem;font-weight:600}
@media(max-width:600px){
  .skill-card{flex-direction:column}
  .skill-card > a{flex:none;align-self:center}
  .skill-card img{width:200px}
}
</style>

欢迎参观我的 AI 百宝箱～ 🧰

总有些事反复折腾我，索性写成 skill 交给 AI 去干，自己用顺手了才放到这儿。

擅长什么、不碰什么都写在里面，合用就带走 👇

全部采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh) 授权：可自由传播和修改，请保留署名，勿用于商业用途。

<!-- entries -->
<div class="skill-card">
  <a href="/pages/skill-library-curator/"><img src="/pages/skill-library-curator/poster.png" alt="Skill 收藏整理器 海报"></a>
  <div class="skill-meta">
    <h3><a href="/pages/skill-library-curator/">Skill 收藏整理器</a></h3>
    <p>把一整个文件夹的 skill 收藏，整理成分好类、编好号、评过分、去过重的一份清单。</p>
    <a class="skill-go" href="/pages/skill-library-curator/">介绍与下载 →</a>
  </div>
</div>
