import re

def main():
    with open('dashboard.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Update HEAD with Tailwind Dark Mode, Theme Script, and CSS changes
    head_replacement = """
    <script>
        // Prevenir flash blanco
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark')
        } else {
            document.documentElement.classList.remove('dark')
        }
    </script>
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    animation: {
                        'progress': 'progress 300s linear forwards',
                    },
                    keyframes: {
                        progress: { '0%': { width: '100%' }, '100%': { width: '0%' } }
                    }
                }
            }
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style type="text/tailwindcss">
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
        body { font-family: 'Plus Jakarta Sans', sans-serif; @apply bg-slate-50 text-slate-800 dark:bg-slate-950 dark:text-slate-200 transition-colors duration-300; }
        
        @layer components {
            .glass-card {
                @apply bg-white/90 backdrop-blur-md border border-slate-200/80 dark:bg-slate-900/90 dark:border-slate-800;
            }
            .card-hover { @apply transition-all duration-300 hover:shadow-xl dark:hover:shadow-indigo-500/10 hover:-translate-y-1; }
            .status-pill { @apply px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider shadow-sm; }
            .badge-ok { @apply bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400; }
            .badge-err { @apply bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-400; }
            .badge-warn { @apply bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400; }
            .badge-info { @apply bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-400; }
            .text-title { @apply text-slate-900 dark:text-white; }
            .text-sub { @apply text-slate-500 dark:text-slate-400; }
            .border-sub { @apply border-slate-200 dark:border-slate-800; }
            .bg-sub { @apply bg-slate-50 dark:bg-slate-900; }
        }

        .status-dot { @apply h-2.5 w-2.5 rounded-full; }
        .custom-scrollbar::-webkit-scrollbar { width: 6px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { @apply bg-slate-200 dark:bg-slate-700 rounded-lg; }

        .glitch-active { @apply ring-4 ring-rose-500/50 relative overflow-hidden; }
        .glitch-active::after { content: ''; position: absolute; inset: 0; background: rgba(244,63,94,0.05); animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; pointer-events: none; }
    </style>
"""
    html = re.sub(r'<script src="https://cdn.tailwindcss.com"></script>.*?</style>', head_replacement, html, flags=re.DOTALL)

    # 2. Update Header: Add Dark Mode Toggle and Progress Bar
    header_right_part = r"""
        <div class="flex items-center gap-6 relative">
            <button id="theme-toggle" class="p-3 bg-white dark:bg-slate-800 rounded-full shadow-sm text-slate-500 dark:text-slate-400 hover:text-indigo-500 transition-colors border border-slate-200 dark:border-slate-700">
                <!-- Sun Icon -->
                <svg id="theme-toggle-light-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" fill-rule="evenodd" clip-rule="evenodd"></path></svg>
                <!-- Moon Icon -->
                <svg id="theme-toggle-dark-icon" class="hidden w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"></path></svg>
            </button>
            
            <div class="text-right px-6 border-r border-slate-200 dark:border-slate-800">
                <p class="text-[10px] font-extrabold text-indigo-500 uppercase tracking-widest mb-1">Última Actualización</p>
                <p id="update-time" class="text-2xl font-mono font-black text-title tracking-tighter">--:--:--</p>
            </div>
            
            <div class="flex flex-col gap-2 relative">
                <label id="btn-cargar-json" class="group bg-slate-900 dark:bg-indigo-600 hover:bg-indigo-600 dark:hover:bg-indigo-500 text-white px-6 py-3 rounded-2xl cursor-pointer flex items-center gap-3 transition-all shadow-lg overflow-hidden z-10 relative">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 group-hover:rotate-12 transition-transform" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                    <span class="font-bold whitespace-nowrap">Cargar JSON</span>
                    <input type="file" id="fileInput" class="hidden" accept=".json">
                    
                    <!-- Progress bar -->
                    <div id="auto-progress" class="absolute bottom-0 left-0 h-1 bg-emerald-400 hidden"></div>
                </label>
                <div id="auto-refresh-tag" class="text-[9px] font-bold text-slate-400 uppercase text-center hidden absolute -bottom-4 w-full">Auto-Refresh: ON</div>
            </div>
        </div>
"""
    html = re.sub(r'<div class="flex items-center gap-6">.*?</div>\s*</header>', header_right_part + '\n    </header>', html, flags=re.DOTALL)

    # Transform global title classes to dynamic Text Classes
    html = html.replace('text-slate-900', 'text-title')
    html = html.replace('text-slate-800', 'text-title')
    html = html.replace('text-slate-500', 'text-sub')
    html = html.replace('border-slate-100', 'border-sub')
    html = html.replace('bg-slate-50', 'bg-sub')
    html = html.replace('text-slate-400', 'text-sub')

    # Fix specific hardcoded text colors in Glass cards inner HTML that I didn't catch
    html = html.replace('text-indigo-900', 'text-indigo-500')
    html = html.replace('text-emerald-900', 'text-emerald-500')

    # 3. Add Event Log Filters
    zabbix_header = r"""
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-bold text-rose-400 italic font-mono tracking-tighter">Event_Stream.log</h2>
                    <div class="flex gap-2">
                        <span class="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
                    </div>
                </div>
                
                <div class="flex gap-2 mb-6" id="alerts-filters">
                    <button data-filter="all" class="px-3 py-1 bg-white/10 hover:bg-white/20 text-white rounded-lg text-[10px] font-bold transition-colors ring-1 ring-white/20 active-filter">Todos</button>
                    <button data-filter="critical" class="px-3 py-1 bg-white/5 hover:bg-rose-500/20 text-white rounded-lg text-[10px] font-bold transition-colors">Critical</button>
                    <button data-filter="warn" class="px-3 py-1 bg-white/5 hover:bg-amber-500/20 text-white rounded-lg text-[10px] font-bold transition-colors">Warning</button>
                </div>
"""
    html = re.sub(
        r'<div class="flex items-center justify-between mb-8">.*?<h2 class="text-xl font-bold text-rose-400 italic font-mono tracking-tighter">Event_Stream.log</h2>.*?</div>',
        zabbix_header,
        html, flags=re.DOTALL
    )

    # 4. Update the javascript for Switch generation, Filters, Glitch state, Theme, and Progress bar
    
    # 4.a Update Switches Table JS for Accordion
    switches_js_orig = r"""
            switches.forEach(s => {
                const isOK = s.status === "OK";
                totalClients \+= parseInt\(s.clientes\) \|\| 0;
                const row = document.createElement\('tr'\);
                row.className = "hover:bg-sub/50 transition-colors";
                row.innerHTML = `
                    <td class="px-8 py-6">
                        <div class="font-extrabold text-title text-sm tracking-tight">\$\{s.nombre\}</div>
                        <div class="text-\[10px\] text-sub font-bold uppercase tracking-widest mt-1">\$\{s.modelo \|\| 'TPLink Managed'\}</div>
                    </td>
                    <td class="px-8 py-6">
                        <span class="status-pill \$\{isOK \? 'badge-ok' : 'badge-err'\}">\$\{s.status\}</span>
                        <div class="text-\[10px\] text-indigo-500 font-mono mt-2 font-black">\$\{s.ip\}</div>
                        <div class="text-\[9px\] text-sub font-mono mt-1 opacity-50">\$\{s.mac \|\| '--'\}</div>
                    </td>
                    <td class="px-8 py-6 text-center">
                        <span class="text-2xl font-black text-title italic">\$\{s.clientes\}</span>
                    </td>
                    <td class="px-8 py-6">
                        <div class="flex items-center gap-6">
                           <div class="min-w-\[80px\]">
                                <div class="flex justify-between text-\[8px\] font-black uppercase text-sub mb-1">
                                    <span>CPU: \$\{s.cpu\}</span>
                                    <span>MEM: \$\{s.mem \|\| '--'\}</span>
                                </div>
                                <div class="w-full bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                    <div class="bg-indigo-600 h-full" style="width: \$\{s.cpu\}"></div>
                                </div>
                           </div>
                           <div class="flex flex-col gap-1">
                                <span class="text-\[9px\] font-mono font-bold text-sub bg-sub/50 px-2 py-0.5 rounded">\$\{s.firmware \|\| 'V.N/A'\}</span>
                                \$\{s.upgrade_disponible \? '<span class="text-\[8px\] text-amber-600 font-black animate-pulse">UPGRADE REQ</span>' : ''\}
                                <span class="text-\[8px\] font-bold text-slate-300 dark:text-slate-600">UPTIME: \$\{s.uptime \|\| '---\'}</span>
                           </div>
                        </div>
                    </td>
                `;
                swTable.appendChild\(row\);
            \}\);"""

    switches_js_new = r"""
            switches.forEach((s, idx) => {
                const isOK = s.status === "OK";
                totalClients += parseInt(s.clientes) || 0;
                
                // Fila principal
                const row = document.createElement('tr');
                row.className = "hover:bg-sub/50 transition-colors cursor-pointer group";
                row.onclick = () => {
                    const extra = document.getElementById(`sw-extra-${idx}`);
                    extra.classList.toggle('hidden');
                };
                row.innerHTML = `
                    <td class="px-8 py-4">
                        <div class="font-extrabold text-title text-sm tracking-tight group-hover:text-indigo-500 transition-colors flex items-center gap-2">
                           <svg class="h-3 w-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" /></svg>
                           ${s.nombre}
                        </div>
                    </td>
                    <td class="px-8 py-4">
                        <span class="status-pill ${isOK ? 'badge-ok' : 'badge-err'}">${s.status}</span>
                        <div class="text-[10px] text-indigo-500 font-mono mt-1 font-black">${s.ip}</div>
                    </td>
                    <td class="px-8 py-4 text-center">
                        <span class="text-xl font-black text-title italic">${s.clientes}</span>
                    </td>
                    <td class="px-8 py-4">
                        <div class="w-full max-w-[80px] bg-slate-100 dark:bg-slate-800 h-1.5 rounded-full overflow-hidden" title="CPU: ${s.cpu}">
                            <div class="bg-indigo-600 h-full" style="width: ${s.cpu}"></div>
                        </div>
                    </td>
                `;
                swTable.appendChild(row);
                
                // Fila Extra Acordeon (oculta inicialmente)
                const extraRow = document.createElement('tr');
                extraRow.id = `sw-extra-${idx}`;
                extraRow.className = "hidden bg-slate-50/30 dark:bg-slate-900/30";
                extraRow.innerHTML = `
                    <td colspan="4" class="px-8 flex py-4 text-[10px] items-start gap-10 border-t border-slate-100/50 dark:border-slate-800/50">
                        <div><p class="font-black text-sub uppercase mb-1">Modelo</p><p class="text-title">${s.modelo || 'TPLink Managed'}</p><p class="font-mono text-sub opacity-50 mt-1">${s.mac || '--'}</p></div>
                        <div><p class="font-black text-sub uppercase mb-1">Hardware</p><p class="text-title">Memoria: ${s.mem || '--'}</p><p class="text-title">CPU: ${s.cpu}</p></div>
                        <div><p class="font-black text-sub uppercase mb-1">Sistema</p><p class="text-title">Uptime: ${s.uptime || 'S/D'}</p><p class="font-mono bg-sub px-1 py-0.5 rounded text-sub">${s.firmware || 'V.N/A'}</p></div>
                        ${s.upgrade_disponible ? '<div class="text-amber-500 font-black animate-pulse flex items-center border border-amber-500/20 bg-amber-500/10 px-3 py-1 rounded-xl">UPGRADE RECOMMENDED</div>' : ''}
                    </td>
                `;
                swTable.appendChild(extraRow);
            });"""

    html = re.sub(r'switches\.forEach\(s => \{.*?\}\);', switches_js_new, html, flags=re.DOTALL)

    # 4.b Update Alert generation to tag them with data-level
    alert_orig = r"""
                const sev = parseInt\(a.severidad\);
                const color = sev >= 4 \? 'text-rose-400' : \(sev >= 3 \? 'text-amber-400' : 'text-indigo-400'\);
                const line = document.createElement\('div'\);
                line.className = "py-2 border-b border-white/5 hover:bg-white/5 transition-colors cursor-default";
                line.innerHTML = `<span class="\$\{color\} font-black">\[LEVEL_\$\{sev\}\]</span> <span class="text-slate-200">\$\{a.evento\}</span>`;
                alertsCont.appendChild\(line\);"""
                
    alert_new = r"""
                const sev = parseInt(a.severidad);
                const color = sev >= 4 ? 'text-rose-400' : (sev >= 3 ? 'text-amber-400' : 'text-indigo-400');
                const lvlclass = sev >= 4 ? 'zbx-crit' : (sev >= 3 ? 'zbx-warn' : 'zbx-info');
                const line = document.createElement('div');
                line.className = `alert-line py-2 border-b border-white/5 hover:bg-white/5 transition-colors cursor-default ${lvlclass}`;
                line.innerHTML = `<span class="${color} font-black">[LEVEL_${sev}]</span> <span class="text-slate-200">${a.evento}</span>`;
                alertsCont.appendChild(line);"""
    
    html = re.sub(r'const sev = parseInt\(a\.severidad\);.*?alertsCont\.appendChild\(line\);', alert_new, html, flags=re.DOTALL)
    
    # 4.c Add Theme and Glitch logic at the bottom of script
    script_end_repl = r"""

        // Global Glitch/Crisis Evaluation
        const mainEl = document.querySelector('header > div:first-child > div:first-child');
        if(pbsHasErrors || switches.some(s => s.status !== "OK")) {
            mainEl.classList.add('animate-pulse', 'bg-rose-500', 'shadow-rose-500');
            mainEl.classList.remove('bg-indigo-600', 'shadow-indigo-200');
            document.body.classList.add('border-t-4', 'border-rose-500');
        } else {
            mainEl.classList.remove('animate-pulse', 'bg-rose-500', 'shadow-rose-500');
            mainEl.classList.add('bg-indigo-600', 'shadow-indigo-200');
            document.body.classList.remove('border-t-4', 'border-rose-500');
        }

    } // end updateDashboard function

    // Filtros Zabbix
    document.querySelectorAll('#alerts-filters button').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // reset styles
            document.querySelectorAll('#alerts-filters button').forEach(b => {
               b.classList.remove('ring-1', 'ring-white/20', 'bg-white/10');
               b.classList.add('bg-white/5');
            });
            e.target.classList.add('ring-1', 'ring-white/20', 'bg-white/10');
            e.target.classList.remove('bg-white/5');
            
            const filter = e.target.getAttribute('data-filter');
            const lines = document.querySelectorAll('.alert-line');
            lines.forEach(l => {
                if(filter === 'all') l.style.display = 'block';
                else if(filter === 'critical') l.style.display = l.classList.contains('zbx-crit') ? 'block' : 'none';
                else if(filter === 'warn') l.style.display = (l.classList.contains('zbx-warn') || l.classList.contains('zbx-crit')) ? 'block' : 'none';
            });
        });
    });

    // Dark Mode Toggle Logic
    const themeToggleBtn = document.getElementById('theme-toggle');
    const darkIcon = document.getElementById('theme-toggle-dark-icon');
    const lightIcon = document.getElementById('theme-toggle-light-icon');

    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        lightIcon.classList.remove('hidden');
    } else {
        darkIcon.classList.remove('hidden');
    }

    themeToggleBtn.addEventListener('click', () => {
        darkIcon.classList.toggle('hidden');
        lightIcon.classList.toggle('hidden');

        if (localStorage.theme === 'light') {
            document.documentElement.classList.add('dark');
            localStorage.theme = 'dark';
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.theme = 'light';
        }
    });

    function restartProgressBar() {
        const pbar = document.getElementById('auto-progress');
        pbar.classList.remove('hidden');
        pbar.classList.remove('animate-progress');
        void pbar.offsetWidth; // trigger reflow
        pbar.classList.add('animate-progress');
    }

"""
    html = re.sub(r'\}\s*function renderChart\(switches\)', script_end_repl + '\n    function renderChart(switches)', html)

    # 4.d Connect progress bar in tryAutoLoad
    html = html.replace("document.getElementById('auto-refresh-tag').classList.remove('hidden');", "document.getElementById('auto-refresh-tag').classList.remove('hidden');\n                    restartProgressBar();")

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("UI Parched Exitosamente")

if __name__ == '__main__':
    main()
