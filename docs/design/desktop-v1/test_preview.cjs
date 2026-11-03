const { chromium }=require(process.env.THEME_QA_PLAYWRIGHT || require("path").join(process.env.TEMP,"medorigin-desktop-theme-qa","node_modules","playwright-core"));
const { pathToFileURL }=require("url");
const path=require("path");
(async()=>{
 const base=__dirname;
 const browser=await chromium.launch({executablePath:"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",headless:true,args:["--no-sandbox"]});
 const widths=[390,768,1024,1280,1440,1920];
 const failures=[];
 try{
  for(const width of widths) {
   const page=await browser.newPage({viewport:{width,height:900},deviceScaleFactor:1});
   const errors=[];page.on("pageerror",e=>errors.push(e.message));
   await page.goto(pathToFileURL(path.join(base,"preview.html")).href,{waitUntil:"networkidle"});
   const initial=await page.evaluate(()=>({w:document.documentElement.scrollWidth,window:innerWidth,theme:document.documentElement.dataset.theme,accent:getComputedStyle(document.documentElement).getPropertyValue('--mo-accent').trim()}));
   if(initial.w>initial.window+2||initial.theme!=="dark"||initial.accent!=="#FF8A45") failures.push([width,"Initial",initial]);
   if(width===1440){await page.screenshot({path:path.join(base,"design-only-dark.png"),fullPage:true});}
   await page.getByRole("button",{name:"Light",exact:true}).click();
   const light=await page.evaluate(()=>({theme:document.documentElement.dataset.theme,accent:getComputedStyle(document.documentElement).getPropertyValue('--mo-accent').trim()}));
   if(light.theme!=="light"||light.accent!=="#C94A05") failures.push([width,"Light",light]);
   if(width===1440){await page.screenshot({path:path.join(base,"design-only-light.png"),fullPage:true});}
   if(width===390){await page.screenshot({path:path.join(base,"design-only-mobile.png"),fullPage:true});}
   await page.getByRole("button",{name:"Evidence",exact:true}).click();
   if(await page.locator("#page-title").textContent()!=="Evidence")failures.push([width,"Nav"]);
   await page.getByRole("searchbox",{name:"Filter capabilities"}).fill("never-exists-xyz");
   const vis=await page.locator(".cap-row:visible").count();
   if(vis!==0)failures.push([width,"Empty search",vis]);
   await page.getByRole("searchbox",{name:"Filter capabilities"}).fill("fhir");
   const matches=await page.locator(".cap-row:visible").count();
   if(matches!==1)failures.push([width,"FHIR search",matches]);
   await page.getByRole("button",{name:"System",exact:true}).click();
   if(await page.locator("html").getAttribute("data-theme")!==null)failures.push([width,"System not honoring OS"]);
   if(errors.length)failures.push([width,"JS errors",errors]);
   await page.close();
  }
  if(failures.length){console.error(JSON.stringify(failures,null,2));process.exitCode=1;}
  else console.log("PASS: 6 browser sizes, theme switching, system preference, navigation, filter and empty state. Three screenshots captured.");
 } finally {await browser.close();}
})().catch(err=>{console.error(err);process.exitCode=1;});
