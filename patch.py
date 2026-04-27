import re

def main():
    with open('dashboard.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Update the link for Cameras
    html = re.sub(
        r'(<h2 class="text-2xl font-black text-slate-900 flex items-center gap-3 italic">\s*Videovigilancia\s*</h2>)',
        r'\1\n                    <a href="http://10.175.6.12/zabbix/" target="_blank" class="px-3 py-1.5 bg-slate-100 hover:bg-indigo-100 text-indigo-600 border border-transparent hover:border-indigo-200 text-[10px] font-black uppercase rounded-lg flex items-center gap-1.5 transition-colors">Abrir Zabbix <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>',
        html
    )

    # 2. Update the link for OPNsense
    html = re.sub(
        r'(<h2 class="text-xl font-extrabold text-slate-900 mb-8 flex items-center gap-3">\s*<svg[^>]*>.*?</svg>\s*Interfaces Firewall \(OPNsense\)\s*</h2>)',
        r'<div class="flex justify-between items-center mb-8">\n                    \1\n                    <a href="https://10.175.6.203" target="_blank" class="px-3 py-1.5 bg-slate-100 hover:bg-emerald-100 text-emerald-600 border border-transparent hover:border-emerald-200 text-[10px] font-black uppercase rounded-lg flex items-center gap-1.5 transition-colors">Abrir OPNsense <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>\n                </div>',
        html, count=1, flags=re.DOTALL
    )
    # clean up the mb-8 from h2 because we moved it to the wrapper
    html = html.replace('<h2 class="text-xl font-extrabold text-slate-900 mb-8 flex items-center gap-3">', '<h2 class="text-xl font-extrabold text-slate-900 flex items-center gap-3">', 1)

    # 3. Update the link for Relojes
    html = re.sub(
        r'(<div class="text-\[10px\] font-bold text-slate-400 uppercase tracking-widest">Sincronización Zabbix</div>)',
        r'<a href="http://10.175.6.12/zabbix/" target="_blank" class="px-3 py-1.5 bg-slate-100 hover:bg-amber-100 text-amber-600 border border-transparent hover:border-amber-200 text-[10px] font-black uppercase rounded-lg flex items-center gap-1.5 transition-colors">Abrir Zabbix <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>',
        html
    )

    # 4. Update the link for PBS
    html = re.sub(
        r'(<div id="pbs-status-badge"[^>]*>.*?</div>)',
        r'\1\n                    <a href="https://10.175.6.2:8007" target="_blank" class="px-3 py-1.5 bg-slate-100 hover:bg-indigo-100 text-indigo-600 border border-transparent hover:border-indigo-200 text-[10px] font-black uppercase rounded-lg flex items-center gap-1.5 transition-colors ml-4">Abrir PBS <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>',
        html
    )
    # wrap right side of pbs header in a flex
    html = re.sub(
        r'(<div id="pbs-status-badge".*?</a>)',
        r'<div class="flex items-center">\n                    \1\n                </div>',
        html, flags=re.DOTALL
    )

    # 5. Update the link for Omada (Switches)
    html = re.sub(
        r'(<p class="text-\[10px\] font-bold text-slate-400 uppercase tracking-\[0\.2em\] mt-1">Managed Switches • TP-Link Omada</p>\n\s*</div>)',
        r'\1\n                    <a href="https://10.175.7.3:8043" target="_blank" class="px-3 py-1.5 bg-slate-100 hover:bg-indigo-100 text-indigo-600 border border-transparent hover:border-indigo-200 text-[10px] font-black uppercase rounded-lg flex items-center gap-1.5 transition-colors">Abrir Omada <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg></a>',
        html
    )

    # 6. Update the Quick Stats Blocks
    # Find the quick stats block and replace it
    new_stats_grid = """
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="glass-card p-4 rounded-3xl card-hover bg-gradient-to-br from-indigo-500 to-indigo-700 text-white border-none flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold opacity-80 uppercase tracking-widest leading-none">Cámaras</p>
                        <div class="bg-white/20 p-1.5 rounded-xl"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" stroke-width="2" /></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="cam-stat" class="text-3xl font-extrabold italic leading-none">--</span><span class="text-[10px] opacity-80 pb-1">Grabando</span></div>
                </div>
                
                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">WiFi Local</p>
                        <div class="bg-indigo-50 p-1.5 rounded-xl text-indigo-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071a9.5 9.5 0 0114.142 0M2.828 9.172a13.5 13.5 0 0118.344 0" stroke-width="2" /></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="client-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span><span class="text-[10px] text-emerald-500 font-bold pb-1">Activos</span></div>
                </div>

                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">Relojes</p>
                        <div class="bg-amber-50 p-1.5 rounded-xl text-amber-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" stroke-width="2" /></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="clock-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span></div>
                </div>

                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">Alertas</p>
                        <div class="bg-rose-50 p-1.5 rounded-xl text-rose-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke-width="2" /></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="alert-stat" class="text-3xl font-extrabold text-rose-600 leading-none">--</span><span id="alert-summary-badge" class="status-pill badge-ok ml-2 mb-1">Clean</span></div>
                </div>

                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">Switches</p>
                        <div class="bg-blue-50 p-1.5 rounded-xl text-blue-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="switch-top-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span></div>
                </div>
                
                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">CAPS & Routers</p>
                        <div class="bg-cyan-50 p-1.5 rounded-xl text-cyan-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="router-top-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span><span class="text-[10px] text-cyan-500 font-bold pb-1">Online</span></div>
                </div>
                
                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">Backups PBS</p>
                        <div class="bg-indigo-50 p-1.5 rounded-xl text-indigo-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"></path></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="pbs-top-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span><span id="pbs-top-badge" class="status-pill badge-ok ml-2 mb-1">OK</span></div>
                </div>
                
                <div class="glass-card p-4 rounded-3xl card-hover flex flex-col justify-between h-[110px]">
                    <div class="flex justify-between items-start">
                        <p class="text-[9px] font-extrabold text-slate-400 uppercase tracking-widest leading-none">Firewall</p>
                        <div class="bg-emerald-50 p-1.5 rounded-xl text-emerald-500"><svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg></div>
                    </div>
                    <div class="flex items-end gap-2"><span id="fw-top-stat" class="text-3xl font-extrabold text-slate-800 leading-none">--</span><span class="text-[10px] text-emerald-500 font-bold pb-1">UP</span></div>
                </div>
            </div>
"""
    html = re.sub(
        r'<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">.*?</div>\s*<!-- Cameras Grid -->',
        f'{new_stats_grid}\n\n            <!-- Cameras Grid -->',
        html, flags=re.DOTALL
    )

    # Now update the javascript logic to fill these new top stats
    js_addon = """
            // TOP STATS OPNsense
            let upFw = 0;
            if(interfaces.length > 0) {
                interfaces.forEach(i => { if(i.status === "up") upFw++; });
            }
            document.getElementById('fw-top-stat').innerText = `${upFw}/${interfaces.length}`;
            
            // TOP STATS Switches
            let okSw = 0;
            switches.forEach(s => { if(s.status === "OK") okSw++; });
            document.getElementById('switch-top-stat').innerText = `${okSw}/${switches.length}`;
            
            // TOP STATS Routers & CAPS
            let onWifi = 0;
            wifiDisps.forEach(d => { if(d.estado === "Online") onWifi++; });
            document.getElementById('router-top-stat').innerText = `${onWifi}/${wifiDisps.length}`;
            
            // TOP STATS PBS
            const topPbsVal = document.getElementById('pbs-top-stat');
            const topPbsBdg = document.getElementById('pbs-top-badge');
            if(pbsHasErrors) {
                topPbsVal.innerText = "ERR";
                topPbsVal.className = "text-3xl font-extrabold text-rose-600 leading-none";
                topPbsBdg.className = "status-pill badge-err ml-2 mb-1 animate-pulse";
                topPbsBdg.innerText = "ACTION";
            } else {
                topPbsVal.innerText = "OK";
                topPbsVal.className = "text-3xl font-extrabold text-slate-800 leading-none";
                topPbsBdg.className = "status-pill badge-ok ml-2 mb-1";
                topPbsBdg.innerText = "SECURE";
            }
"""
    # Let's cleanly inject it before the chart render
    html = html.replace('if(switches.length > 0) renderChart(switches);', f'{js_addon}\n            if(switches.length > 0) renderChart(switches);')

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Dashboard actualizado correctamente.")

if __name__ == '__main__':
    main()
