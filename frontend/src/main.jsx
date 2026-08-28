import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
} from "recharts";
import { request, token } from "./api";
import "./styles.css";

const weekdayNames = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];

function ProgressRing({ value, threshold }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="ring" style={{"--p": `${bounded * 3.6}deg`}}>
      <div>
        <strong>{value.toFixed(1)}%</strong>
        <span>min {threshold}%</span>
      </div>
    </div>
  );
}

function Auth({ onDone }) {
  const [mode, setMode] = useState("login");
  const [colleges, setColleges] = useState([]);
  const [msg, setMsg] = useState("");
  const [form, setForm] = useState({
    name:"", email:"", password:"", college_id:"",
    collegeName:"", min:75, start:"2026-08-01", end:"2026-12-20"
  });

  useEffect(() => { request("/colleges").then(setColleges).catch(()=>{}); }, []);

  async function createCollege() {
    setMsg("");
    try {
      const c = await request("/colleges", {
        method:"POST",
        body: JSON.stringify({
          name: form.collegeName,
          min_attendance_percent: Number(form.min),
          semester_start: form.start,
          semester_end: form.end,
          lab_min_percent: null,
          theory_min_percent: null,
          condonation_min_percent: null
        })
      });
      setColleges(x => [...x.filter(v => v.id !== c.id), c]);
      setForm(f => ({...f, college_id:String(c.id)}));
    } catch(e) { setMsg(e.message); }
  }

  async function submit(e) {
    e.preventDefault(); setMsg("");
    try {
      const data = await request(`/auth/${mode}`, {
        method:"POST",
        body: JSON.stringify(mode === "login"
          ? {email:form.email, password:form.password}
          : {name:form.name, email:form.email, password:form.password, college_id:Number(form.college_id)}
        )
      });
      localStorage.setItem("attendease_token", data.access_token);
      onDone();
    } catch(e) { setMsg(e.message); }
  }

  return <div className="authShell">
    <div className="authCard">
      <div className="brand">Attend<span>Ease</span></div>
      <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
      <p className="muted">Know exactly when you can skip — and when you cannot.</p>

      <form onSubmit={submit}>
        {mode === "signup" && <input placeholder="Your name" value={form.name}
          onChange={e=>setForm({...form,name:e.target.value})} required />}
        <input type="email" placeholder="Email" value={form.email}
          onChange={e=>setForm({...form,email:e.target.value})} required />
        <input type="password" placeholder="Password" value={form.password}
          onChange={e=>setForm({...form,password:e.target.value})} required />

        {mode === "signup" && <>
          <select value={form.college_id} onChange={e=>setForm({...form,college_id:e.target.value})} required>
            <option value="">Select college</option>
            {colleges.map(c=><option key={c.id} value={c.id}>{c.name} — {c.min_attendance_percent}%</option>)}
          </select>
          <details>
            <summary>College not listed? Create it</summary>
            <div className="createCollege">
              <input placeholder="College name" value={form.collegeName}
                onChange={e=>setForm({...form,collegeName:e.target.value})}/>
              <input type="number" min="0" max="100" value={form.min}
                onChange={e=>setForm({...form,min:e.target.value})}/>
              <label>Semester start<input type="date" value={form.start}
                onChange={e=>setForm({...form,start:e.target.value})}/></label>
              <label>Semester end<input type="date" value={form.end}
                onChange={e=>setForm({...form,end:e.target.value})}/></label>
              <button type="button" className="secondary" onClick={createCollege}>Create college</button>
            </div>
          </details>
        </>}
        <button>{mode === "login" ? "Log in" : "Sign up"}</button>
      </form>

      {msg && <div className="error">{msg}</div>}
      <button className="textBtn" onClick={()=>setMode(mode === "login" ? "signup" : "login")}>
        {mode === "login" ? "New here? Create account" : "Already have an account? Log in"}
      </button>
    </div>
  </div>
}

function SubjectForm({ onSaved }) {
  const [form,setForm] = useState({
    name:"", code:"", class_type:"lecture", weekly_schedule:[0,2,4], custom_threshold:""
  });
  const [msg,setMsg]=useState("");

  function toggleDay(d) {
    setForm(f => ({...f, weekly_schedule: f.weekly_schedule.includes(d)
      ? f.weekly_schedule.filter(x=>x!==d) : [...f.weekly_schedule,d]}));
  }

  async function submit(e) {
    e.preventDefault(); setMsg("");
    try {
      await request("/subjects", {method:"POST", body:JSON.stringify({
        ...form,
        custom_threshold: form.custom_threshold === "" ? null : Number(form.custom_threshold)
      })});
      setForm({name:"",code:"",class_type:"lecture",weekly_schedule:[0,2,4],custom_threshold:""});
      onSaved();
    } catch(e){setMsg(e.message)}
  }

  return <form className="panel" onSubmit={submit}>
    <h3>Add subject</h3>
    <div className="grid2">
      <input placeholder="Subject name" value={form.name} onChange={e=>setForm({...form,name:e.target.value})} required/>
      <input placeholder="Code" value={form.code} onChange={e=>setForm({...form,code:e.target.value})}/>
      <select value={form.class_type} onChange={e=>setForm({...form,class_type:e.target.value})}>
        <option value="lecture">Lecture</option>
        <option value="lab">Lab</option>
        <option value="tutorial">Tutorial</option>
      </select>
      <input type="number" min="0" max="100" step=".1" placeholder="Custom threshold (optional)"
        value={form.custom_threshold} onChange={e=>setForm({...form,custom_threshold:e.target.value})}/>
    </div>
    <div className="weekdays">
      {weekdayNames.map((n,i)=><button key={n} type="button"
        className={form.weekly_schedule.includes(i) ? "day active":"day"}
        onClick={()=>toggleDay(i)}>{n}</button>)}
    </div>
    <button>Add subject</button>
    {msg && <div className="error">{msg}</div>}
  </form>
}

function MarkAttendance({ subjects, onSaved }) {
  const today = new Date().toISOString().slice(0,10);
  const [date,setDate] = useState(today);
  const [status,setStatus] = useState("present");
  const [subjectId,setSubjectId] = useState("");
  const [msg,setMsg]=useState("");

  async function submit(e) {
    e.preventDefault(); setMsg("");
    try {
      await request("/attendance", {method:"POST", body:JSON.stringify({
        subject_id:Number(subjectId), date, status
      })});
      setMsg("Saved");
      onSaved();
    } catch(e){setMsg(e.message)}
  }

  async function allPresent() {
    setMsg("");
    try {
      await Promise.all(subjects.map(s => request("/attendance", {
        method:"POST",
        body:JSON.stringify({subject_id:s.id,date,status:"present"})
      })));
      setMsg("All subjects marked present");
      onSaved();
    } catch(e){setMsg(e.message)}
  }

  return <form className="panel" onSubmit={submit}>
    <h3>Mark attendance</h3>
    <div className="grid2">
      <select value={subjectId} onChange={e=>setSubjectId(e.target.value)} required>
        <option value="">Choose subject</option>
        {subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
      </select>
      <input type="date" max={today} value={date} onChange={e=>setDate(e.target.value)}/>
      <select value={status} onChange={e=>setStatus(e.target.value)}>
        <option value="present">Present</option>
        <option value="absent">Absent</option>
        <option value="cancelled">Cancelled</option>
        <option value="holiday">Holiday</option>
      </select>
    </div>
    <div className="actions">
      <button>Save attendance</button>
      <button type="button" className="secondary" onClick={allPresent}>Mark all present</button>
    </div>
    {msg && <div className="info">{msg}</div>}
  </form>
}

function Simulator({ subjects }) {
  const [subjectId,setSubjectId]=useState("");
  const [plan,setPlan]=useState(["absent"]);
  const [result,setResult]=useState(null);

  async function simulate() {
    if(!subjectId) return;
    const r = await request("/simulate", {method:"POST", body:JSON.stringify({
      subject_id:Number(subjectId), future_results:plan
    })});
    setResult(r);
  }

  return <div className="panel">
    <h3>What-if simulator</h3>
    <select value={subjectId} onChange={e=>setSubjectId(e.target.value)}>
      <option value="">Choose subject</option>
      {subjects.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
    </select>
    <div className="simRow">
      <button className="secondary" onClick={()=>setPlan([...plan,"present"])}>+ Attend</button>
      <button className="secondary" onClick={()=>setPlan([...plan,"absent"])}>+ Skip</button>
      <button className="secondary" onClick={()=>setPlan([])}>Clear</button>
    </div>
    <p className="muted">Plan: {plan.length ? plan.map(x=>x==="present"?"✓":"×").join(" ") : "No future classes selected"}</p>
    <button onClick={simulate}>Simulate</button>
    {result && <div className={`projection ${result.status}`}>
      Projected attendance: <strong>{result.attendance_percent.toFixed(1)}%</strong>
      <span>{result.attended}/{result.held} classes</span>
    </div>}
  </div>
}

function SubjectCard({ s }) {
  const message = s.attendance_percent >= s.threshold
    ? `You can miss ${s.safe_misses} more scheduled class${s.safe_misses===1?"":"es"} and remain at or above ${s.threshold}%.`
    : s.recovery_possible
      ? `Attend the next ${s.classes_to_recover} class${s.classes_to_recover===1?"":"es"} to recover to ${s.threshold}%.`
      : `Recovery to ${s.threshold}% is not possible within the estimated remaining schedule.`;

  return <div className={`subjectCard ${s.status}`}>
    <div className="subjectTop">
      <div><h3>{s.name}</h3><span>{s.code || s.class_type}</span></div>
      <ProgressRing value={s.attendance_percent} threshold={s.threshold}/>
    </div>
    <div className="metrics">
      <div><strong>{s.attended}/{s.held}</strong><span>attended</span></div>
      <div><strong>{s.safe_misses}</strong><span>safe misses</span></div>
      <div><strong>{s.recovery_possible ? s.classes_to_recover : "!"}</strong><span>to recover</span></div>
      <div><strong>{s.remaining_estimated}</strong><span>remaining est.</span></div>
    </div>
    <p className="explain">{message}</p>
  </div>
}

function Dashboard({ user, stats }) {
  const trend = stats.subjects.map((s,i)=>({name:s.code||s.name.slice(0,8), percent:s.attendance_percent}));
  return <>
    <section className="hero">
      <div>
        <p className="eyebrow">{user.college.name}</p>
        <h1>Good afternoon, {user.name.split(" ")[0]}.</h1>
        <p>Minimum overall attendance: <strong>{user.college.min_attendance_percent}%</strong></p>
      </div>
      <div className={`overallBox ${stats.overall.status}`}>
        <ProgressRing value={stats.overall.attendance_percent} threshold={stats.overall.threshold}/>
        <div>
          <strong>Overall attendance</strong>
          <span>{stats.overall.attended}/{stats.overall.held} held classes</span>
          {stats.overall.attendance_percent >= stats.overall.threshold
            ? <span>You can currently miss {stats.overall.safe_misses} more.</span>
            : <span>{stats.overall.recovery_possible ? `Attend ${stats.overall.classes_to_recover} consecutive classes to recover.` : "Recovery may be impossible this semester."}</span>}
        </div>
      </div>
    </section>

    <h2>Your subjects</h2>
    <div className="cards">
      {stats.subjects.length ? stats.subjects.map(s=><SubjectCard key={s.subject_id} s={s}/>)
        : <div className="empty">Add your first subject below to start tracking.</div>}
    </div>

    {!!trend.length && <div className="panel chartPanel">
      <h3>Current attendance by subject</h3>
      <div style={{width:"100%",height:240}}>
        <ResponsiveContainer>
          <LineChart data={trend}>
            <XAxis dataKey="name"/>
            <YAxis domain={[0,100]}/>
            <Tooltip/>
            <Line type="monotone" dataKey="percent" strokeWidth={3}/>
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>}
  </>
}

function App() {
  const [ready,setReady]=useState(false);
  const [user,setUser]=useState(null);
  const [subjects,setSubjects]=useState([]);
  const [stats,setStats]=useState(null);
  const [tab,setTab]=useState("dashboard");
  const [error,setError]=useState("");

  async function load() {
    try {
      const [u,s,st] = await Promise.all([request("/me"),request("/subjects"),request("/stats")]);
      setUser(u); setSubjects(s); setStats(st); setError("");
    } catch(e) {
      localStorage.removeItem("attendease_token");
      setUser(null); setError(e.message);
    } finally { setReady(true); }
  }

  useEffect(()=>{ if(token()) load(); else setReady(true); },[]);

  if(!ready) return <div className="loading">Loading AttendEase…</div>;
  if(!user) return <Auth onDone={load}/>;

  return <div>
    <header>
      <div className="brand">Attend<span>Ease</span></div>
      <nav>
        {["dashboard","mark","subjects","simulator"].map(t=><button key={t}
          className={tab===t?"active":""} onClick={()=>setTab(t)}>
          {t[0].toUpperCase()+t.slice(1)}
        </button>)}
      </nav>
      <button className="logout" onClick={()=>{localStorage.removeItem("attendease_token");setUser(null)}}>Log out</button>
    </header>

    <main>
      {tab==="dashboard" && stats && <Dashboard user={user} stats={stats}/>}
      {tab==="mark" && <MarkAttendance subjects={subjects} onSaved={load}/>}
      {tab==="subjects" && <>
        <SubjectForm onSaved={load}/>
        <div className="panel">
          <h3>Current subjects</h3>

          {subjects.map(s => (
            <div className="subjectRow" key={s.id}>
              <div>
                <strong>{s.name}</strong>
                <span>
                  {s.code || "No code"} · {s.class_type}
                </span>
              </div>
        
              <span>
                {s.weekly_schedule.map(x => weekdayNames[x]).join(", ") || "No schedule"}
              </span>
        
              <button
                className="deleteBtn"
                onClick={async () => {
                  const confirmed = window.confirm(
                    `Delete ${s.name}? This will also delete its attendance records.`
                  );
        
                  if (!confirmed) return;
        
                  try {
                    await request(`/subjects/${s.id}`, {
                      method: "DELETE"
                    });
        
                    await load();
                  } catch (e) {
                    alert(e.message);
                  }
                }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </>}
      {tab==="simulator" && <Simulator subjects={subjects}/>}
    </main>
  </div>
}

createRoot(document.getElementById("root")).render(<App/>);
