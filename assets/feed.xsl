<?xml version="1.0" encoding="UTF-8"?>
<!--
  给 Atom 订阅源套一层可读的皮。

  浏览器从 2013 年前后就不再渲染 RSS/Atom 了，直接点开只会看到一屏 XML 源码。
  挂上这张样式表后，人用浏览器打开是正常网页，而 RSS 阅读器抓取时会忽略样式表，
  照常解析 XML。两边互不影响。
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:atom="http://www.w3.org/2005/Atom">

  <xsl:output method="html" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/atom:feed">
    <html lang="zh-CN">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta name="robots" content="noindex"/>
        <title><xsl:value-of select="atom:title"/> · 订阅源</title>
        <style>
          :root{
            --bg:#ffffff; --fg:#1f2328; --muted:#6a737d;
            --border:#e5e7eb; --card:#f8f9fa; --accent:#C0821E;
          }
          @media (prefers-color-scheme: dark){
            :root{
              --bg:#1b1b1e; --fg:#d5d5d6; --muted:#87878b;
              --border:#2f2f33; --card:#212125; --accent:#E8A33D;
            }
          }
          *{box-sizing:border-box;margin:0;padding:0}
          body{
            background:var(--bg);color:var(--fg);
            font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
            line-height:1.7;padding:48px 20px 80px;
          }
          .wrap{max-width:680px;margin:0 auto}
          .badge{
            display:inline-block;font-size:.74rem;letter-spacing:.12em;
            color:var(--accent);border:1px solid var(--accent);
            padding:3px 10px;border-radius:20px;margin-bottom:18px;
          }
          h1{font-size:1.7rem;line-height:1.3;margin-bottom:8px;font-weight:700}
          .sub{color:var(--muted);font-size:.95rem;margin-bottom:28px}
          .box{
            background:var(--card);border:1px solid var(--border);
            border-radius:12px;padding:20px 22px;margin-bottom:34px;
          }
          .box h2{font-size:1rem;margin-bottom:10px;font-weight:600}
          .box p{color:var(--muted);font-size:.9rem;margin-bottom:14px}
          .url{
            display:flex;gap:10px;align-items:center;flex-wrap:wrap;
          }
          .url code{
            flex:1;min-width:220px;
            font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
            font-size:.84rem;background:var(--bg);color:var(--fg);
            border:1px solid var(--border);border-radius:8px;
            padding:9px 12px;overflow-x:auto;white-space:nowrap;
          }
          .url button{
            font:inherit;font-size:.84rem;cursor:pointer;
            background:var(--accent);color:#1b1b1e;border:0;
            border-radius:8px;padding:9px 18px;font-weight:600;
          }
          .url button:active{transform:translateY(1px)}
          h3.sec{
            font-size:.78rem;letter-spacing:.1em;color:var(--muted);
            text-transform:uppercase;margin-bottom:14px;font-weight:600;
          }
          .entry{
            padding:16px 0;border-bottom:1px solid var(--border);
          }
          .entry:last-child{border-bottom:0}
          .entry a{
            color:var(--fg);text-decoration:none;font-size:1.05rem;
            font-weight:600;line-height:1.4;
          }
          .entry a:hover{color:var(--accent)}
          .entry .date{
            font-size:.78rem;color:var(--muted);margin-top:5px;
            font-variant-numeric:tabular-nums;
          }
          .entry .summary{
            font-size:.88rem;color:var(--muted);margin-top:7px;
          }
          footer{
            margin-top:40px;padding-top:20px;border-top:1px solid var(--border);
            font-size:.85rem;color:var(--muted);
          }
          footer a{color:var(--accent);text-decoration:none}
        </style>
      </head>
      <body>
        <div class="wrap">
          <div class="badge">RSS 订阅源</div>
          <h1><xsl:value-of select="atom:title"/></h1>
          <p class="sub"><xsl:value-of select="atom:subtitle"/></p>

          <div class="box">
            <h2>这是给阅读器用的地址</h2>
            <p>复制下面这串地址，粘贴到你的 RSS 阅读器（Feedly、Inoreader、NetNewsWire 等），
               以后有新文章会自动推送给你，不用记着回来看。</p>
            <div class="url">
              <code id="feed-url"><xsl:value-of select="atom:link[@rel='self']/@href"/></code>
              <button type="button" onclick="copyFeed(this)">复制</button>
            </div>
          </div>

          <h3 class="sec">最近更新</h3>
          <xsl:for-each select="atom:entry">
            <div class="entry">
              <a>
                <xsl:attribute name="href">
                  <xsl:value-of select="atom:link/@href"/>
                </xsl:attribute>
                <xsl:value-of select="atom:title"/>
              </a>
              <div class="date">
                <xsl:value-of select="substring(atom:published,1,10)"/>
              </div>
              <div class="summary">
                <xsl:value-of select="atom:summary"/>
              </div>
            </div>
          </xsl:for-each>

          <footer>
            <a>
              <xsl:attribute name="href">
                <xsl:value-of select="atom:link[@rel='alternate']/@href"/>
              </xsl:attribute>
              ← 回到博客
            </a>
          </footer>
        </div>
        <script>
          function copyFeed(btn){
            var t = document.getElementById('feed-url').textContent.trim();
            var done = function(){
              btn.textContent = '已复制';
              setTimeout(function(){ btn.textContent = '复制'; }, 2000);
            };
            if (navigator.clipboard &amp;&amp; window.isSecureContext) {
              navigator.clipboard.writeText(t).then(done).catch(function(){ fb(t, done); });
            } else { fb(t, done); }
          }
          function fb(text, cb){
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;left:-9999px';
            document.body.appendChild(ta); ta.select();
            try { document.execCommand('copy'); cb(); } catch(e) { alert('复制失败，请手动选中复制'); }
            document.body.removeChild(ta);
          }
        </script>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
