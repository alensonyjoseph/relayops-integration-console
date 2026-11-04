import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity, ArrowLeftRight, ArrowRight, ArrowUpRight, BarChart3,
  BookOpen, Check, CheckCheck, ChevronDown, ChevronRight, CircleAlert, CircleCheck,
  ClipboardCheck, Code2, Database, ExternalLink, GitBranch, Github, Layers3,
  Menu, Package, Play, Plus, RadioTower, RotateCcw, Search,
  ShieldCheck, Sparkles, Terminal, Truck, X, Zap,
  type LucideIcon,
} from 'lucide-react'
import { api } from './lib/api'
import { runScenario, type Scenario } from './lib/scenarios'
import { sampleEvents, sampleMetrics, sampleShipments, scenarioDescriptions } from './data/sample'
import type { ApiStep, Metrics, OperationalEvent, Shipment, ShipmentStatus, Tab } from './types'

const repo = 'https://github.com/alensonyjoseph/relayops-integration-console'
const navigation: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id:'overview', label:'Overview', icon:BarChart3 },
  { id:'shipments', label:'Shipments', icon:Package },
  { id:'laboratory', label:'Event laboratory', icon:Terminal },
  { id:'diagnostics', label:'Diagnostics', icon:Activity },
]
const emptyMetrics: Metrics = {shipments:0,accepted:0,rejected:0,duplicates:0,processed:0}
const statusOrder: ShipmentStatus[] = ['CREATED','PICKED_UP','IN_TRANSIT','DELIVERED']
const fmt = (v: string) => v.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, x => x.toUpperCase())
function when(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? '—' : date.toLocaleString(undefined, {month:'short', day:'numeric', hour:'2-digit',minute:'2-digit'})
}
function StatusBadge({ status }: {status:string}) {
  const kind = status === 'ACCEPTED' || status === 'DELIVERED' ? 'success' :
    status === 'REJECTED' || status === 'CANCELLED' ? 'danger' :
    status === 'IN_TRANSIT' ? 'info' : 'neutral'
  return <span className={'badge badge-' + kind}><span className="badge-dot"/>{fmt(status)}</span>
}
function Panel({ title, subtitle, action, children, className='' }: {
  title:string; subtitle?:string; action?:ReactNode; children:ReactNode; className?:string
}) {
  return <section className={'panel ' + className}>
    <div className="panel-head"><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
    {children}
  </section>
}
function MetricCard({ label, value, foot, icon: Icon, tone }: {label:string;value:number;foot:string;icon:LucideIcon;tone:string}) {
  return <div className="metric-card">
    <div className="metric-top"><span>{label}</span><span className={'metric-icon metric-icon-' + tone}><Icon size={18}/></span></div>
    <strong>{value.toLocaleString()}</strong>
    <div className="metric-foot"><span className={'foot-mark foot-' + tone}><ArrowUpRight size={13}/></span>{foot}</div>
  </div>
}
function EventTable({ events, compact=false }: {events:OperationalEvent[];compact?:boolean}) {
  return <div className="table-scroll"><table className="data-table">
    <thead><tr><th>Event identity</th><th>Shipment</th><th>Requested state</th><th>Outcome</th>{!compact&&<th>Reason / time</th>}</tr></thead>
    <tbody>{events.length ? events.map((e,i) => <tr key={e.id || e.event_id + i}>
      <td><span className="code-line">{e.event_id}</span><small>{e.source}</small></td>
      <td className="semibold">{e.shipment_ref}</td>
      <td><span className="state-mono">{e.requested_status}</span></td>
      <td><StatusBadge status={e.outcome}/></td>
      {!compact && <td className="muted-cell">{e.rejection_reason || when(e.received_at || e.occurred_at)}</td>}
    </tr>) : <tr><td colSpan={compact ? 4 : 5} className="empty-table">No events yet. Load sample data or run a scenario.</td></tr>}</tbody>
  </table></div>
}
function StatusTimeline({status}:{status:ShipmentStatus}) {
  const current = statusOrder.indexOf(status)
  return <div className="state-timeline">{statusOrder.map((s,i) =>
    <div className={'state-item '+(i <= current && current !== -1?'active':'')} key={s}>
      <span className="state-point">{i < current ? <Check size={12}/> : i+1}</span>
      <span>{fmt(s)}</span>{i<3&&<span className="state-connector"/>}
    </div>)}</div>
}
export default function App() {
  const [tab,setTab] = useState<Tab>('overview')
  const [mobileOpen,setMobileOpen] = useState(false)
  const [online,setOnline] = useState<'checking'|'connected'|'offline'>('checking')
  const [data,setData] = useState<Metrics>(emptyMetrics)
  const [shipments,setShipments] = useState<Shipment[]>([])
  const [events,setEvents] = useState<OperationalEvent[]>([])
  const [selected,setSelected] = useState<string|null>(null)
  const [detail,setDetail] = useState<{shipment:Shipment,events:OperationalEvent[]}|null>(null)
  const [search,setSearch] = useState('')
  const [createOpen,setCreateOpen] = useState(false)
  const [newReference,setNewReference] = useState('')
  const [newPartner,setNewPartner] = useState('')
  const [scenario,setScenario] = useState<Scenario>('collision')
  const [steps,setSteps] = useState<ApiStep[]>([])
  const [busy,setBusy] = useState(false)
  const [message,setMessage] = useState('')
  const [expandedStep,setExpandedStep] = useState(0)

  const refresh = useCallback(async () => {
    try {
      await api<{status:string}>('/api/health')
      const [metrics, shipResult, eventResult] = await Promise.all([
        api<Metrics>('/api/metrics'),
        api<{shipments:Shipment[]}>('/api/shipments'),
        api<{events:OperationalEvent[]}>('/api/events'),
      ])
      setData(metrics);setShipments(shipResult.shipments);setEvents(eventResult.events)
      setOnline('connected')
      return true
    } catch {
      setOnline('offline')
      return false
    }
  },[])
  useEffect(()=>{ void refresh() },[refresh])

  const preview=online!=='connected'
  const m=preview ? sampleMetrics : data
  const rows=preview ? sampleShipments : shipments
  const eventRows=preview ? sampleEvents : events
  const filtered=useMemo(()=>rows.filter(s=>[s.reference,s.partner,s.status].join(' ').toLowerCase().includes(search.toLowerCase())),[rows,search])
  const selectedItem=rows.find(s=>s.reference===selected)
  const graphItems=[
    {label:'Accepted',value:m.accepted,color:'var(--teal)'},
    {label:'Rejected',value:m.rejected,color:'var(--coral)'},
    {label:'Replays',value:m.duplicates,color:'var(--violet)'},
  ]
  const maxGraph=Math.max(1,...graphItems.map(x=>x.value))

  function navigate(next:Tab) {
    setTab(next);setMobileOpen(false);setMessage('')
  }
  async function seedDemo() {
    if (online!=='connected') return
    setBusy(true);setMessage('')
    try {
      const r=await api<{created_shipments:number}>('/api/demo/seed',{})
      await refresh()
      setMessage(r.created_shipments ? 'Six synthetic shipments loaded successfully.' : 'Sample dataset already loaded in this workspace.')
    } catch(e) {setMessage(e instanceof Error?e.message:'Could not load demo data.')}
    finally {setBusy(false)}
  }
  async function resetDemo(){
    if(online!=='connected') return
    setBusy(true);setMessage('')
    try{ await api('/api/demo/reset',{});await refresh();setSteps([]);setSelected(null);setDetail(null);setMessage('This browser workspace was reset.')}
    catch(e){setMessage(e instanceof Error?e.message:'Reset failed.')}
    finally{setBusy(false)}
  }
  async function createShipment(){
    setBusy(true);setMessage('')
    try{
      await api('/api/shipments',{reference:newReference.trim().toUpperCase(),partner:newPartner.trim()})
      setCreateOpen(false);setNewReference('');setNewPartner('')
      await refresh();setMessage('Shipment created and ready for events.')
    }catch(e){setMessage(e instanceof Error?e.message:'Could not create shipment.')}
    finally{setBusy(false)}
  }
  async function chooseShipment(ref:string){
    setSelected(ref);setDetail(null)
    if(online!=='connected') return
    try{
      const d=await api<{shipment:Shipment,events:OperationalEvent[]}>( '/api/shipments/'+encodeURIComponent(ref))
      setDetail(d)
    }catch(e){setMessage(e instanceof Error?e.message:'Could not load shipment.')}
  }
  async function executeScenario(){
    if(online!=='connected') return
    setBusy(true);setMessage('');setSteps([])
    try{
      const result=await runScenario(scenario)
      setSteps(result);setExpandedStep(Math.max(0,result.length-1))
      await refresh()
      setMessage('Real HTTP requests completed. Inspect each recorded response below.')
    }catch(e){setMessage(e instanceof Error?e.message:'Scenario failed.')}
    finally{setBusy(false)}
  }
  const brand=<div className="brand"><div className="brand-icon"><ArrowLeftRight size={25} strokeWidth={2.5}/></div>
    <div><strong>relay<span>ops</span></strong><small>INTEGRATION RELIABILITY</small></div></div>

  return <div className="app-shell">
    <aside className={'sidebar '+(mobileOpen?'sidebar-open':'')}>
      <div className="sidebar-top">{brand}<button className="sidebar-close icon-button" aria-label="Close menu" onClick={()=>setMobileOpen(false)}><X size={18}/></button></div>
      <div className="workspace-selector"><span className="workspace-mark"><Layers3 size={17}/></span>
        <div><strong>Demo workspace</strong><small>Synthetic data only</small></div><ChevronDown size={15}/></div>
      <div className="nav-caption">WORKSPACE</div>
      <nav className="nav-items" aria-label="Main navigation">
        {navigation.map(({id,label,icon:Icon})=><button key={id} onClick={()=>navigate(id)} className={'nav-button '+(tab===id?'active':'')}>
          <Icon size={18}/><span>{label}</span>{id==='diagnostics'&&<span className="nav-indicator"/>}</button>)}
      </nav>
      <div className="sidebar-note"><span className="note-mark"><ShieldCheck size={17}/></span>
        <strong>Built for reliability.</strong><p>Reproducible failures. Explicit state rules. Verified fixes.</p>
        <button onClick={()=>navigate('laboratory')}>Open event lab <ArrowRight size={14}/></button>
      </div>
      <div className="sidebar-bottom">
        <a href={repo} target="_blank" rel="noreferrer"><Github size={17}/> Source on GitHub <ExternalLink size={13}/></a>
        <a href={repo+'/blob/main/docs/architecture.md'} target="_blank" rel="noreferrer"><BookOpen size={17}/> Architecture docs <ExternalLink size={13}/></a>
        <div className="side-version"><span className="live-dot"/> RelayOps v1.0 <span>Portfolio project</span></div>
      </div>
    </aside>
    {mobileOpen&&<button className="mobile-shade" aria-label="Close navigation" onClick={()=>setMobileOpen(false)}/>}
    <div className="main-shell">
      <header className="topbar"><div className="topbar-left">
        <button className="mobile-menu icon-button" aria-label="Open navigation" onClick={()=>setMobileOpen(true)}><Menu size={20}/></button>
        <span className="crumb-root">Workspace</span><ChevronRight size={15}/><span className="crumb-current">{navigation.find(x=>x.id===tab)?.label}</span>
      </div><div className="topbar-right">
        <span className={'connection '+(online==='connected'?'connected':online==='checking'?'checking':'disconnected')}><span/>{online==='connected'?'API connected':online==='checking'?'Checking API':'Design preview'}</span>
        <a className="icon-button header-github" href={repo} target="_blank" rel="noreferrer" aria-label="GitHub repository"><Github size={19}/></a>
        <div className="avatar">AS</div>
      </div></header>
      <main className="content">
        {preview && <div className="preview-notice"><CircleAlert size={18}/><div><strong>{online==='checking'?'Connecting to the backend…':'Showing sample data — interactive API not connected'}</strong><span>{online==='checking'?'Waiting for database health check.':'The interface is a design preview until the Flask API and PostgreSQL database are configured. The sample values are illustrative.'}</span></div><button onClick={()=>void refresh()}>Retry <RotateCcw size={14}/></button></div>}
        {message&&<div className="inline-message" role="status"><CircleCheck size={17}/><span>{message}</span><button aria-label="Dismiss message" onClick={()=>setMessage('')}><X size={16}/></button></div>}
        {tab==='overview'&&<>
          <div className="page-eyebrow"><span className="eyebrow-line"/> OPERATIONS INTELLIGENCE / OVERVIEW</div>
          <div className="page-heading"><div><h1>Every event. Accounted for.</h1><p>Observe, trace and verify your integration pipeline with confidence.</p></div>
            <button className="btn btn-dark" onClick={()=>navigate('laboratory')}><Play size={15} fill="currentColor"/> Run scenario <ArrowRight size={15}/></button></div>
          <div className="hero-card"><div className="hero-glow"/><div className="hero-content">
            <span className="hero-label"><Sparkles size={14}/> ENGINEERING SHOWCASE</span>
            <h2>Reliable events.<br/><em>Explainable outcomes.</em></h2>
            <p>See how strict validation, idempotency and state transitions protect a shipment pipeline from bad data.</p>
            <button onClick={()=>navigate('diagnostics')} className="hero-link">Explore the regression proof <ArrowRight size={17}/></button>
          </div><div className="hero-visual" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/>
            <div className="hero-node n1"><Truck size={19}/></div><div className="hero-node n2"><ShieldCheck size={21}/></div><div className="hero-node n3"><Database size={19}/></div>
            <div className="hero-center"><ArrowLeftRight size={27}/></div><span className="hero-pulse hp1"/><span className="hero-pulse hp2"/>
          </div></div>
          <div className="section-subtitle"><div><h2>System at a glance</h2><span>Operational totals · {preview?'illustrative dataset':'your browser workspace'}</span></div>
            <button className="link-button" onClick={()=>void refresh()}><RotateCcw size={14}/> Refresh</button></div>
          <div className="metrics-grid">
            <MetricCard label="Events processed" value={m.processed} foot="Including retries" icon={Activity} tone="indigo"/>
            <MetricCard label="Accepted" value={m.accepted} foot="State changes applied" icon={CheckCheck} tone="mint"/>
            <MetricCard label="Rejected" value={m.rejected} foot="Invalid or stale events" icon={ShieldCheck} tone="coral"/>
            <MetricCard label="Duplicate replays" value={m.duplicates} foot="Side effects prevented" icon={ArrowLeftRight} tone="violet"/>
          </div>
          <div className="dashboard-grid">
            <Panel title="Processing distribution" subtitle="By disposition, across recorded events">
              <div className="graph">
                {graphItems.map(item=><div className="graph-row" key={item.label}><div className="graph-label"><span>{item.label}</span><strong>{item.value}</strong></div>
                  <div className="graph-track"><span style={{width:(item.value/maxGraph*100)+'%',background:item.color}}/></div></div>)}
              </div>
              <div className="graph-footer"><span className="graph-pin"/><span>{m.processed} processed attempts</span><span className="graph-footer-right">Live totals when connected</span></div>
            </Panel>
            <Panel title="Pipeline safeguards" subtitle="Controls applied to every incoming event">
              <div className="safeguard-list">
                {[{icon:ShieldCheck,title:'Schema validation',desc:'Reject malformed or unexpected fields'},
                  {icon:ArrowLeftRight,title:'Idempotency keys',desc:'Exact retries without duplicate mutations'},
                  {icon:GitBranch,title:'State transitions',desc:'Only authorised changes are persisted'},
                  {icon:Database,title:'Transactional audit',desc:'Changes and evidence committed together'}].map(item=>
                  <div className="safeguard" key={item.title}><span className="safeguard-icon"><item.icon size={18}/></span><div><strong>{item.title}</strong><small>{item.desc}</small></div><Check size={16} className="safeguard-check"/></div>)}
              </div>
            </Panel>
          </div>
          <Panel title="Recent activity" subtitle="Latest external integration events" action={<button className="link-button" onClick={()=>navigate('shipments')}>View shipments <ArrowRight size={15}/></button>}>
            <EventTable events={eventRows.slice(0,5)} compact/>
          </Panel>
          {!preview&&m.shipments===0&&<div className="empty-workspace"><div className="empty-illustration"><Package size={24}/></div><div><strong>Your workspace is empty</strong><span>Load six synthetic shipments and their event history to explore the system.</span></div><button className="btn btn-accent" onClick={()=>void seedDemo()} disabled={busy}><Plus size={16}/> Load sample data</button></div>}
        </>}
        {tab==='shipments'&&<>
          <div className="page-eyebrow"><span className="eyebrow-line"/> EVENT PIPELINE / RECORDS</div>
          <div className="page-heading"><div><h1>Shipment explorer</h1><p>Inspect status, transitions and the evidence behind every update.</p></div>
            <button disabled={preview||busy} className="btn btn-dark" onClick={()=>setCreateOpen(true)}><Plus size={16}/> New shipment</button></div>
          <div className="records-card"><div className="records-bar"><div className="search-field"><Search size={18}/><input aria-label="Search shipments" placeholder="Search reference, partner, status…" value={search} onChange={e=>setSearch(e.target.value)}/></div>
            <div className="records-count">{filtered.length} shipments</div></div>
            <div className="table-scroll"><table className="data-table shipment-table"><thead><tr><th>Reference</th><th>Integration partner</th><th>Status</th><th>Version</th><th>Last accepted event</th><th/></tr></thead>
              <tbody>{filtered.map(s=><tr key={s.reference} className="click-row" onClick={()=>void chooseShipment(s.reference)}>
                <td><span className="record-id"><span className="record-dot"><Package size={15}/></span>{s.reference}</span></td>
                <td>{s.partner}</td><td><StatusBadge status={s.status}/></td><td className="muted-cell">v{s.version}</td><td className="muted-cell">{when(s.last_event_at)}</td>
                <td><ChevronRight size={17}/></td></tr>)}
                {!filtered.length&&<tr><td colSpan={6} className="empty-table">No matching shipments.</td></tr>}</tbody>
            </table></div>
            <div className="records-footer">{preview?'Illustrative preview data':'Shipment records come directly from PostgreSQL'}
              {!preview&&<div><button onClick={()=>void seedDemo()} disabled={busy}>Load sample dataset</button><button onClick={()=>void resetDemo()} disabled={busy}>Reset workspace</button></div>}</div>
          </div>
          <Panel title="Event inbox" subtitle="Accepted and rejected events, newest first"><EventTable events={eventRows}/></Panel>
          {selectedItem&&<div className="drawer-shade" onClick={()=>{setSelected(null);setDetail(null)}}><aside className="detail-drawer" onClick={e=>e.stopPropagation()}><div className="drawer-top"><div><small>SHIPMENT DETAILS</small><h2>{selectedItem.reference}</h2></div><button className="icon-button" onClick={()=>setSelected(null)} aria-label="Close shipment detail"><X size={20}/></button></div>
            <div className="drawer-banner"><Truck size={28}/><div><span>Current state</span><StatusBadge status={selectedItem.status}/></div></div>
            <div className="drawer-section"><h3>Progress timeline</h3><StatusTimeline status={selectedItem.status}/></div>
            <div className="drawer-properties"><div><span>Integration partner</span><strong>{selectedItem.partner}</strong></div><div><span>Version</span><strong>{selectedItem.version}</strong></div><div><span>Latest event</span><strong>{when(selectedItem.last_event_at)}</strong></div></div>
            <div className="drawer-section"><h3>Event history</h3>{detail?.events.length ? detail.events.map(e=><div className="drawer-event" key={e.event_id}><div><StatusBadge status={e.outcome}/><small>{e.event_id}</small></div><p>{e.requested_status}{e.rejection_reason?' · '+e.rejection_reason:''}</p></div>) : <p className="drawer-muted">{preview?'Example data — event details require the API.':'No events for this shipment yet.'}</p>}</div>
          </aside></div>}
          {createOpen&&<div className="modal-shade" onClick={()=>setCreateOpen(false)}><section className="modal" onClick={e=>e.stopPropagation()}><div className="modal-header"><h2>Create synthetic shipment</h2><button className="icon-button" aria-label="Close" onClick={()=>setCreateOpen(false)}><X size={19}/></button></div>
            <p>Use fictional data only. New shipments start in the CREATED state.</p>
            <label>Shipment reference<input value={newReference} onChange={e=>setNewReference(e.target.value)} placeholder="SHIP-EXAMPLE01"/></label>
            <label>Integration partner<input value={newPartner} onChange={e=>setNewPartner(e.target.value)} placeholder="Example Freight"/></label>
            <button className="btn btn-dark" disabled={busy||!newReference.trim()||!newPartner.trim()} onClick={()=>void createShipment()}>Create shipment <ArrowRight size={16}/></button></section></div>}
        </>}
        {tab==='laboratory'&&<>
          <div className="page-eyebrow"><span className="eyebrow-line"/> VERIFICATION WORKBENCH / EVENT LAB</div>
          <div className="page-heading"><div><h1>Break it. Then prove it.</h1><p>Run real API scenarios and inspect the exact HTTP responses.</p></div>
            <span className="lab-live"><span/> REAL BACKEND REQUESTS</span></div>
          <div className="lab-intro"><div><span className="lab-intro-icon"><Zap size={23}/></span><div><strong>Interactive integration laboratory</strong><p>Each run creates an isolated synthetic shipment, executes the selected request sequence and records its outcome. Nothing is simulated when the API is connected.</p></div></div></div>
          <div className="lab-grid">
            <Panel title="Choose a failure scenario" subtitle="One reproducible workflow at a time" className="scenario-panel">
              <div className="scenario-list">{(Object.keys(scenarioDescriptions) as Scenario[]).map((key,i)=><button className={'scenario-item '+(scenario===key?'scenario-selected':'')} key={key} onClick={()=>{setScenario(key);setSteps([])}}>
                <span className="scenario-number">{String(i+1).padStart(2,'0')}</span><span className="scenario-copy"><strong>{scenarioDescriptions[key].title}</strong><small>{scenarioDescriptions[key].subtitle}</small></span><ChevronRight size={17}/></button>)}</div>
            </Panel>
            <Panel title="Scenario inspector" subtitle="Request → database outcome → response" className="inspector-panel">
              <div className="inspector-label"><span className="inspector-pill"><RadioTower size={13}/> ACTIVE SCENARIO</span><span>HTTP / JSON</span></div>
              <h2>{scenarioDescriptions[scenario].title}</h2><p className="inspector-description">{scenarioDescriptions[scenario].why}</p>
              <div className="scenario-route"><div className="route-node"><span>01</span><strong>Ingest</strong><small>HTTP request</small></div><ArrowRight size={20}/><div className="route-node"><span>02</span><strong>Validate</strong><small>Domain rules</small></div><ArrowRight size={20}/><div className="route-node"><span>03</span><strong>Decide</strong><small>Transaction</small></div></div>
              <button className="btn btn-accent btn-full" disabled={busy||preview} onClick={()=>void executeScenario()}><Play size={16} fill="currentColor"/>{busy?'Executing requests…':'Run live scenario'}<ArrowRight size={16}/></button>
              {preview&&<div className="lab-disconnected"><CircleAlert size={16}/> Connect Flask + PostgreSQL to enable live execution.</div>}
              {steps.length>0 ? <div className="lab-results"><div className="result-heading"><strong>Execution trace</strong><span>{steps.length} HTTP requests</span></div>
                {steps.map((s,i)=><div className="trace-step" key={i}><button onClick={()=>setExpandedStep(expandedStep===i?-1:i)}><span className={'http-badge '+(s.http<300?'http-ok':s.http<500?'http-warn':'http-bad')}>{s.http}</span><span>{s.label}</span><ChevronDown size={16}/></button>{expandedStep===i&&<div className="trace-code"><strong>REQUEST</strong><pre>{JSON.stringify(s.request,null,2)}</pre><strong>RESPONSE</strong><pre>{JSON.stringify(s.response,null,2)}</pre></div>}</div>)}
              </div> : <div className="empty-trace"><Code2 size={25}/><strong>Your trace will appear here</strong><span>Execute a scenario to inspect its real request and response sequence.</span></div>}
            </Panel>
          </div>
          <Panel title="What this proves" subtitle="Engineering capabilities shown by the running demonstration">
            <div className="proof-grid">{[{icon:Database,title:'Database consistency',desc:'Atomic shipment changes and matching audit records'},
              {icon:ShieldCheck,title:'Boundary validation',desc:'Strict Pydantic schemas and explicit error contracts'},
              {icon:ArrowLeftRight,title:'Idempotency',desc:'Retry detection using canonical payload fingerprints'}].map(x=><div className="proof-item" key={x.title}><span><x.icon size={20}/></span><strong>{x.title}</strong><small>{x.desc}</small></div>)}</div>
          </Panel>
        </>}
        {tab==='diagnostics'&&<>
          <div className="page-eyebrow"><span className="eyebrow-line"/> ENGINEERING EVIDENCE / DIAGNOSTICS</div>
          <div className="page-heading"><div><h1>A failure you can reproduce.</h1><p>A real regression test for a subtle, costly integration bug.</p></div>
            <a href={repo+'/blob/main/backend/tests/test_processing.py'} className="btn btn-dark" target="_blank" rel="noreferrer"><Code2 size={16}/> View test source <ExternalLink size={15}/></a></div>
          <div className="diagnostic-feature"><div className="diag-icon"><CircleAlert size={26}/></div><div><span className="diag-eyebrow">REGRESSION CASE 001 · IDENTITY COLLISION</span><h2>Same event ID. Different payload.</h2><p>An external carrier retries an event identifier but changes its status. A naive deduplication check silently accepts the second request, hiding a conflicting update. RelayOps compares a canonical payload fingerprint and responds with <code>409 Conflict</code>, leaving shipment state unchanged.</p></div></div>
          <div className="comparison-grid">
            <div className="compare-card compare-bad"><div className="compare-top"><span className="compare-icon"><X size={17}/></span><span>NAIVE IMPLEMENTATION</span></div><h3>Silently accepts conflict</h3><pre>{'if event_id in processed_ids:\n    return {"ok": True}  # BUG'}</pre><p>The client sees success even though the same identity now means something different.</p><span className="compare-footer"><CircleAlert size={15}/> Information lost</span></div>
            <div className="compare-card compare-good"><div className="compare-top"><span className="compare-icon"><Check size={17}/></span><span>RELAYOPS IMPLEMENTATION</span></div><h3>Fail with explicit evidence</h3><pre>{'if stored.hash != incoming.hash:\n    raise EVENT_ID_CONFLICT  # 409'}</pre><p>The state is preserved; the error is deterministic and testable.</p><span className="compare-footer"><ShieldCheck size={15}/> Integrity preserved</span></div>
          </div>
          <div className="diagnostic-grid">
            <Panel title="Validation contract" subtitle="Why the backend makes safe decisions">
              <div className="contract-list">{[
                ['201 Created','New valid event applied','success'],
                ['200 OK','Identical retry, no second mutation','success'],
                ['409 Conflict','Same event ID but changed payload','danger'],
                ['422 Unprocessable','Stale or forbidden state transition','warn'],
                ['400 Bad Request','Malformed input or invalid schema','warn'],
              ].map(([http,what,tone])=><div className="contract-item" key={http}><span className={'contract-http contract-'+tone}>{http}</span><span>{what}</span></div>)}</div>
            </Panel>
            <Panel title="Verification artefacts" subtitle="Inspectable code and tests">
              <div className="artifact-list">{[
                {name:'Regression test',desc:'Collision and exact-retry assertions',path:'backend/tests/test_processing.py',icon:ClipboardCheck},
                {name:'Transition rules',desc:'Pure Python deterministic state machine',path:'backend/relayops/domain.py',icon:GitBranch},
                {name:'Database migration',desc:'Relationships, constraints and indices',path:'backend/migrations/versions/0001_initial.py',icon:Database},
                {name:'Architecture',desc:'Trade-offs and processing sequence',path:'docs/architecture.md',icon:Layers3},
              ].map(x=><a key={x.name} href={repo+'/blob/main/'+x.path} target="_blank" rel="noreferrer"><span className="artifact-icon"><x.icon size={18}/></span><div><strong>{x.name}</strong><small>{x.desc}</small></div><ExternalLink size={15}/></a>)}</div>
            </Panel>
          </div>
          <div className="diag-bottom"><div><span className="diag-bottom-mark"><ShieldCheck size={24}/></span><div><strong>Every claim should be inspectable.</strong><p>This is synthetic portfolio software. Code, tests, migrations and engineering decisions are publicly available for independent review.</p></div></div><a href={repo} target="_blank" rel="noreferrer">Explore source <ArrowUpRight size={17}/></a></div>
        </>}
        <footer className="page-footer"><span><ArrowLeftRight size={15}/> RelayOps <span className="footer-dot"/> Engineering portfolio demonstration</span><span>Built with Python · PostgreSQL · React · TypeScript</span></footer>
      </main>
    </div>
  </div>
}
