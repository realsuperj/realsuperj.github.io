---
# the default layout is 'page'
icon: fas fa-toolbox
order: 4
---

<style>
/* 整张卡片是唯一入口。卡内不再放任何独立链接 —— 图、标题、按钮三个入口
   指向同一个地方，读者要先判断点哪个，反而是负担。 */
.skill-card{
  display:flex;gap:20px;align-items:center;position:relative;
  padding:18px 22px;margin:18px 0;
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
/* 用图标而不是海报缩略图：128px 宽的海报根本看不清字，而且所有 skill
   共用一套模板，缩略图彼此长得一样，连区分作用都起不到。海报的用武之地
   是介绍页顶部和转发，不是这里。 */
.skill-icon{
  flex:0 0 56px;width:56px;height:56px;border-radius:14px;
  display:flex;align-items:center;justify-content:center;
  font-size:1.45rem;color:#C0821E;
  background:rgba(232,163,61,.10);border:1px solid rgba(232,163,61,.24);
}
/* Chirpy 7.6 起用 Bootstrap 的 data-bs-theme 记录主题，不再是 data-mode */
html[data-bs-theme="dark"] .skill-icon{color:#E8A33D}
.skill-body{flex:1;min-width:0}
.skill-body h3{margin:0 0 7px;font-size:1.16rem;line-height:1.35;transition:color .18s}
.skill-card:hover .skill-body h3{color:var(--link-color)}
.skill-body p{margin:0;font-size:.91rem;line-height:1.7;color:var(--text-muted-color,#6c757d)}
.skill-tags{display:flex;gap:7px;flex-wrap:wrap;margin-top:11px}
.skill-tag{
  font-size:.72rem;padding:2.5px 9px;border-radius:20px;line-height:1.6;
  color:var(--text-muted-color,#6c757d);
  background:rgba(128,128,128,.10);
  border:1px solid var(--main-border-color,#e9ecef);
}
/* 日期钉在右上角：跟在标签后面的话，标签数量一变位置就漂，
   多张卡片并排会参差不齐。钉住之后自然对齐成一列。 */
.skill-date{
  position:absolute;top:14px;right:20px;
  font-size:.8rem;color:var(--text-muted-color,#6c757d);opacity:.75;
  font-variant-numeric:tabular-nums;letter-spacing:.02em;
}
.skill-arrow{
  flex:0 0 auto;font-size:1.35rem;line-height:1;
  color:var(--text-muted-color,#6c757d);opacity:.35;
  transition:opacity .18s,transform .18s,color .18s;
}
.skill-card:hover .skill-arrow{opacity:1;transform:translateX(4px);color:var(--link-color)}
@media(max-width:640px){
  .skill-card{flex-direction:column;align-items:flex-start;gap:14px;padding:18px}
  .skill-arrow{display:none}
  .skill-date{position:static;order:3;opacity:.5}
}
</style>

欢迎参观我的 AI 百宝箱～ 🧰

总有些事反复折腾我，索性写成 skill 交给 AI 去干，自己用顺手了才放到这儿。

擅长什么、不碰什么都写在里面，合用就带走 👇

全部采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh) 授权：可自由传播和修改，请保留署名，勿用于商业用途。

<div class="skill-list">
<!-- entries -->
<a class="skill-card" href="/pages/periodic-report-assistant/">
  <span class="skill-date">2026-09-13</span>
  <span class="skill-icon"><i class="fas fa-calendar-week"></i></span>
  <div class="skill-body">
    <h3>周期汇报助手</h3>
    <p>把零散材料按天记下，到点生成可直接复制的周报、月报和阶段汇报。</p>
    <div class="skill-tags">
      <span class="skill-tag">周期汇报</span>
      <span class="skill-tag">可追溯</span>
    </div>
  </div>
  <span class="skill-arrow">→</span>
</a>

<a class="skill-card" href="/pages/skill-library-curator/">
  <span class="skill-date">2026-08-31</span>
  <span class="skill-icon"><i class="fas fa-folder-tree"></i></span>
  <div class="skill-body">
    <h3>Skill 收藏整理器</h3>
    <p>把一整个文件夹的 skill 收藏，整理成分好类、编好号、评过分、去过重的一份清单。</p>
    <div class="skill-tags">
      <span class="skill-tag">文件管理</span>
      <span class="skill-tag">增量更新</span>
    </div>
  </div>
  <span class="skill-arrow">→</span>
</a>
</div>
