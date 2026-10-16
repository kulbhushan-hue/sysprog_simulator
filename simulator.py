"""Rule-based z/OS console / TSO / SDSF / SMP/E simulator. Pure Python, no external APIs."""
import re, time, difflib

def now(): return time.strftime("%H.%M.%S")
DATE = "2026.281"

ABENDS = {
 "S0C1": "Operation exception: branch into data/garbage; check entry point or corrupt load module.",
 "S0C4": "Protection exception: program touched storage it does not own; check PSW and failing instruction.",
 "S0C7": "Data exception: invalid packed/zoned decimal in a numeric field; find the field and its contents.",
 "S0CB": "Decimal divide exception: divide by zero or overflow; check the divisor.",
 "S222": "Job cancelled by operator/TSO user; check the log for who and why.",
 "S322": "CPU time limit exceeded: TIME too small or program looped.",
 "S806": "Module not found: wrong program name or library missing from STEPLIB/link list.",
 "S878": "Not enough virtual storage: increase REGION or look for storage leaks.",
 "S913": "RACF security violation: read the ICH408I message for dataset/resource and access.",
}
KNOWN_DSN = {"SYS1.PARMLIB": "SYSRES", "SYS1.PARMLIB.BACKUP": "SYSRES", "SYS1.PARMLIB.TEST": "USRP01",
             "SYS1.LINKLIB": "SYSRES", "USER01.TEST.DATA": "USRP01", "USER01.TEST.COPY": "USRP01",
             "USER.TEST.AUTHLIB": "USRP01"}
JCL_OUT = {
 "ALLOC": "IEF142I ALLOC STEP1 - STEP WAS EXECUTED - COND CODE 0000\nIEF285I   USER01.TEST.DATA   CATALOGED\nIEF285I   VOL SER NOS= USRP01",
 "COPY": "IEF142I COPY STEP1 - STEP WAS EXECUTED - COND CODE 0000\nIEF285I   USER01.TEST.COPY   CATALOGED",
 "COMPRESS": "IEF142I COMPRESS STEP1 - STEP WAS EXECUTED - COND CODE 0000\nIEB147I END OF JOB - 0 WAS HIGHEST SEVERITY CODE",
 "DEFVSAM": "IDC0508I DATA ALLOCATION STATUS FOR VOLUME USRP01 IS 0\nIDC0001I FUNCTION COMPLETED, HIGHEST CONDITION CODE WAS 0",
 "DUMP": "ADR006I STARTING DUMP ... ADR013I 'DUMP' TASK COMPLETED SUCCESSFULLY, RC 0000",
 "LISTVTOC": "DUMP OF VTOC ENTRIES FOR DATA SETS ON VOLUME USRP01\n THERE ARE 00012345 EMPTY CYLINDERS ON THIS VOLUME",
}
CATALOG = ["D IPLINFO", "D A,L", "D PARMLIB", "D GRS,C", "D R,L", "D M=CPU", "D M=STOR", "D PROG,APF", "D PROG,LNKLST",
 "D U,,ALLOC,0A82", "V 0A82,ONLINE", "SET PROG=01", "SETPROG APF,ADD,DSNAME=USER.TEST.AUTHLIB,VOLUME=USRP01",
 "SETPROG LNKLST,DEFINE,NAME=LNKLST02,COPYFROM=CURRENT", "F LLA,REFRESH", "S MYPROC", "P MYPROC", "C MYJOB1",
 "$DJ1234", "$DI", "$DSPOOL", "$DCKPTDEF", "$HJ1234", "$AJ1234", "LISTCAT ENTRIES('SYS1.PARMLIB') ALL",
 "LISTUSER USER01", "LISTDSD DATASET('USER01.TEST.**') ALL", "SUBMIT ALLOC", "SDSF DA", "SDSF ST", "SDSF LOG",
 "RECEIVE SELECT(UK12345)", "APPLY SELECT(UK12345) CHECK", "APPLY SELECT(UK12345)", "ACCEPT SELECT(UK12345)",
 "RESTORE SELECT(UK12345)", "LIST SYSMODS", "REPORT ERRSYSMODS", "ABEND S0C7", "RMF", "IPL", "HELP"]
HELP = "Try: " + "\n     ".join(", ".join(CATALOG[i:i+4]) for i in range(0, len(CATALOG), 4))

class SysState:
    def __init__(s): s.reset()
    def reset(s):
        s.apf = [("SYS1.LINKLIB", "SYSRES"), ("SYS1.SVCLIB", "SYSRES"), ("SYS1.MIGLIB", "SYSRES")]
        s.lnk = {"LNKLST00": ["SYS1.LINKLIB", "SYS1.MIGLIB", "CEE.SCEERUN"]}; s.lnk_active = "LNKLST00"
        s.tasks = {k: "ACTIVE" for k in ["JES2", "VTAM", "TCPIP", "RACF", "LLA", "VLF"]}
        s.jobs = {"JOB01234": dict(name="MYJOB1", q="EXECUTION", c="A", held=False),
                  "JOB01235": dict(name="MYJOB2", q="PRINT", c="A", held=False),
                  "JOB01236": dict(name="MYJOB3", q="EXECUTION", c="B", held=False),
                  "JOB01237": dict(name="MYJOB4", q="AWAITING", c="A", held=False)}
        s.inits = {1: ["A"], 2: ["A", "B"], 3: ["B"]}; s.init_on = {1: True, 2: True, 3: True}
        s.dev = {"0A82": True}; s.smpe = dict(received=set(), applied=set(), accepted=set())
        s.spool = {"SPOOL1": 37, "SPOOL2": 12}

def _jid(n): return "JOB%05d" % int(n)

def execute(s, raw):
    c = " ".join(raw.strip().upper().split())
    if not c: return ""
    t, st = now(), {}
    def M(p):
        m = re.match(p, c); st["m"] = m; return m
    if M(r"^HELP$"): return HELP
    if M(r"^IPL$"):
        return ("IEA371I SYS1.IPLPARM ON DEVICE 0A82 SELECTED FOR IPL PARAMETERS\nIEA246I LOAD ID 00 SELECTED\n"
                "IEA008I SYSTEM PARAMETERS FROM IEASYS00\n*00 IEA101A SPECIFY SYSTEM PARAMETERS FOR RELEASE z/OS 03.01.00\n"
                "Reply with:  R 00,CLPA   (then at $HASP426:  R 01,NOREQ)")
    if M(r"^R (\d+),(\S+)$"):
        n, a = st["m"].groups()
        extra = "\nIXC418I SYSTEM SYSA IS NOW ACTIVE IN SYSPLEX PLEX1\n*01 $HASP426 SPECIFY OPTIONS - HASP-II 3.1" if n == "00" else "\n$HASP400 ENTER REQUESTS -\n$HASP373 JES2 STARTED"
        return f"IEE600I REPLY TO {n} IS;{a}{extra}"
    # ---- display commands
    if M(r"^D IPLINFO$"):
        return ("IEE254I %s IPLINFO DISPLAY\n SYSTEM IPLED AT 07.58.01 ON 10/06/2026\n RELEASE z/OS 03.01.00    LICENSE = z/OS\n"
                " USED LOAD02 IN SYS0.IPLPARM ON 0A82\n IEASYM LIST = XX\n IEASYS LIST = (00,01) (OP)\n"
                " IPL DEVICE: ORIGINAL(0A82) CURRENT(0A82) VOLUME(SYSRES)") % t
    if M(r"^D A,L$"):
        rows = [f" {k:<8} {k:<8} {k:<8} NSW  S" for k, v in s.tasks.items() if v == "ACTIVE"]
        rows += [f" {j['name']:<8} STEP1    CALC     NSW  SO" for j in s.jobs.values() if j["q"] == "EXECUTION"]
        return (f"IEE114I {t} {DATE} ACTIVITY 211\n JOBS    M/S    TS USERS  SYSAS  INITS  ACTIVE/MAX VTAM  OAS\n"
                f" 00004   00027  00002     00045  00015  00002/00020       00021\n" + "\n".join(rows))
    if M(r"^D A,(\w+)$"):
        n = st["m"].group(1)
        return f"IEE115I {t} {DATE} ACTIVITY\n {n} ACTIVE" if s.tasks.get(n) == "ACTIVE" or any(j["name"] == n for j in s.jobs.values()) else f"IEE341I {n} NOT ACTIVE"
    if M(r"^D PARMLIB$"):
        return (f"IEE251I {t} PARMLIB DISPLAY\n PARMLIB DATA SETS SPECIFIED AT IPL\n ENTRY FLAGS VOLUME DATA SET\n"
                "     1   S   SYSRES SYS1.PARMLIB\n     2   D   USRP01 SYS2.PARMLIB\n     3   S   SYSRES SYS1.IBM.PARMLIB\n FLAGS: S = SYSTEM, D = DYNAMIC")
    if M(r"^D GRS,C$"): return f"ISG343I {t} GRS STATUS  NO ENQ CONTENTION EXISTS (simulated)"
    if M(r"^D R,L$"): return "IEE112I NO OUTSTANDING REPLIES"
    if M(r"^D M=CPU$"): return f"IEE174I {t} DISPLAY M\n PROCESSOR STATUS\n ID  CPU  SERIAL\n 00  +    01234A\n 01  +    01234A\n + ONLINE"
    if M(r"^D M=STOR$"): return f"IEE174I {t} DISPLAY M\n REAL STORAGE STATUS\n ONLINE-NOT RECONFIGURABLE 0M-16384M"
    if M(r"^D PROG,APF(,DSNAME=(\S+))?$"):
        f = st["m"].group(2); rows = [(i + 1, v, d) for i, (d, v) in enumerate(s.apf) if not f or d == f]
        if f and not rows: return f"CSV450I {t} PROG,APF DISPLAY\n {f} NOT IN APF LIST"
        return f"CSV450I {t} PROG,APF DISPLAY\n ENTRY VOLUME DSNAME\n" + "\n".join(f" {i:>4}  {v:<6} {d}" for i, v, d in rows)
    if M(r"^D PROG,LNKLST$"):
        return f"CSV470I {t} LNKLST DISPLAY - LNKLST SET {s.lnk_active}\n" + "\n".join(f" {i+1:>3}  {d}" for i, d in enumerate(s.lnk[s.lnk_active]))
    if M(r"^D U,,ALLOC,(\w+)$"): return f"IEE106I {t} UNIT STATUS\n {st['m'].group(1)} ALLOCATED TO: (none)"
    if M(r"^D PROG,\*$"): return execute(s, "D PROG,APF") + "\n" + execute(s, "D PROG,LNKLST")
    # ---- vary / set / setprog
    if M(r"^V (\w{3,4}),(ONLINE|OFFLINE)$"):
        d, a = st["m"].groups(); s.dev[d] = a == "ONLINE"; return f"IEE302I {d}     {a}"
    if M(r"^SET PROG=(\w\w)$"): return f"IEE252I MEMBER PROG{st['m'].group(1)} FOUND IN SYS1.PARMLIB\nPROGxx activated (simulated)"
    if M(r"^SETPROG APF,ADD,DSNAME=([^,]+),(SMS|VOLUME=(\w+))$"):
        d, _, v = st["m"].groups()
        if any(x[0] == d for x in s.apf): return f"CSV411I {d} ALREADY IN APF LIST"
        s.apf.append((d, v or "SMS")); return f"CSV410I DATA SET {d} ADDED TO APF LIST"
    if M(r"^SETPROG APF,DELETE,DSNAME=([^,]+)(,.*)?$"):
        d = st["m"].group(1); s.apf = [x for x in s.apf if x[0] != d]; return f"DATA SET {d} REMOVED FROM APF LIST"
    if M(r"^SETPROG LNKLST,DEFINE,NAME=(\w+),COPYFROM=CURRENT$"):
        n = st["m"].group(1); s.lnk[n] = list(s.lnk[s.lnk_active]); return f"LNKLST SET {n} DEFINED (simulated)"
    if M(r"^SETPROG LNKLST,ADD,NAME=(\w+),DSNAME=(\S+)$"):
        n, d = st["m"].groups()
        if n not in s.lnk: return f"LNKLST SET {n} NOT DEFINED - run DEFINE first"
        s.lnk[n].append(d); return f"{d} ADDED TO {n} (simulated)"
    if M(r"^SETPROG LNKLST,ACTIVATE,NAME=(\w+)$"):
        n = st["m"].group(1)
        if n not in s.lnk: return f"LNKLST SET {n} NOT DEFINED"
        s.lnk_active = n; return f"LNKLST SET {n} ACTIVATED. Now run F LLA,REFRESH."
    if M(r"^F LLA,REFRESH$"): return "LLA REFRESH COMPLETE (simulated)"
    if M(r"^K A,\d+$"): return "Console area display updated (simulated)"
    # ---- tasks
    if M(r"^S (\w{1,8})(,.*)?$"):
        n = st["m"].group(1); s.tasks[n] = "ACTIVE"; return f"IEF403I {n} - STARTED - TIME={t}"
    if M(r"^P (\w{1,8})$"):
        n = st["m"].group(1)
        if s.tasks.get(n) != "ACTIVE": return f"IEE341I {n} NOT ACTIVE"
        s.tasks[n] = "STOPPED"; return f"IEF404I {n} - ENDED - TIME={t}"
    if M(r"^C (\w{1,8})(,A=\w+)?$"):
        n = st["m"].group(1)
        for k, j in list(s.jobs.items()):
            if j["name"] == n: del s.jobs[k]; return f"IEE301I {n} CANCEL COMMAND ACCEPTED\nIEF450I {n} STEP1 - ABEND=S222 U0000"
        if s.tasks.get(n) == "ACTIVE": s.tasks[n] = "STOPPED"; return f"IEE301I {n} CANCEL COMMAND ACCEPTED"
        return f"IEE341I {n} NOT ACTIVE"
    # ---- JES2
    if M(r"^\$D ?J ?(\d+)$"):
        k = _jid(st["m"].group(1)); j = s.jobs.get(k)
        return f"$HASP890 JOB({k}) JOBNAME={j['name']},QUEUE={j['q']},CLASS={j['c']},{'HELD' if j['held'] else 'NOT HELD'}" if j else f"$HASP003 RC=(52) {k} NOT FOUND"
    if M(r"^\$([HAPC]) ?J ?(\d+)$"):
        a, n = st["m"].groups(); k = _jid(n)
        if k not in s.jobs: return f"$HASP003 RC=(52) {k} NOT FOUND"
        if a == "H": s.jobs[k]["held"] = True; return f"$HASP000 JOB({k}) HELD"
        if a == "A": s.jobs[k]["held"] = False; return f"$HASP000 JOB({k}) RELEASED"
        del s.jobs[k]; return f"$HASP000 JOB({k}) {'CANCELLED' if a == 'C' else 'PURGED'}"
    if M(r"^\$T ?J ?(\d+),C(LASS)?=(\w)$"):
        k = _jid(st["m"].group(1))
        if k not in s.jobs: return f"$HASP003 RC=(52) {k} NOT FOUND"
        s.jobs[k]["c"] = st["m"].group(3); return f"$HASP000 JOB({k}) CLASS CHANGED TO {st['m'].group(3)}"
    if M(r"^\$DI$"):
        return "\n".join(f"$HASP892 INIT({i}) STATUS={'ACTIVE' if s.init_on[i] else 'DRAINED'},CLASS={''.join(v)}" for i, v in s.inits.items())
    if M(r"^\$([SP])I ?(\d)$"):
        a, i = st["m"].groups(); i = int(i)
        if i not in s.inits: return f"$HASP003 INIT({i}) NOT FOUND"
        s.init_on[i] = a == "S"; return f"$HASP000 INIT({i}) {'STARTED' if a == 'S' else 'DRAINING'}"
    if M(r"^\$T ?I ?(\d),CLASS=(\w+)$"):
        i, cl = int(st["m"].group(1)), st["m"].group(2)
        if i not in s.inits: return f"$HASP003 INIT({i}) NOT FOUND"
        s.inits[i] = list(cl); return f"$HASP000 INIT({i}) CLASS={cl}"
    if M(r"^\$D ?SPOOL$"): return "\n".join(f"$HASP893 VOLUME({v}) STATUS=ACTIVE,PERCENT={p}" for v, p in s.spool.items()) + "\n(keep volumes below ~70-80%)"
    if M(r"^\$D ?CKPTDEF$"): return "$HASP829 CKPTDEF CKPT1=(DSNAME=SYS1.JES2.CKPT1,VOLSER=SPOOL1),CKPT2=(DSNAME=SYS1.JES2.CKPT2,VOLSER=SPOOL2),MODE=DUPLEX (simulated)"
    if M(r"^\$T ?CKPTDEF,RECONFIG=YES$"): return "$HASP233 CHECKPOINT RECONFIGURATION DIALOG STARTED (simulated)"
    if M(r"^\$P ?JES2$"): return "$HASP607 JES2 SHUTDOWN requires drained initiators and stopped applications. Use with care (simulated: not executed)."
    # ---- TSO / IDCAMS / RACF
    if M(r"^LISTCAT ENTRIES\('?([^')]+)'?\)( ALL)?$"):
        d = st["m"].group(1)
        if d not in KNOWN_DSN: return f"IDC3012I ENTRY {d} NOT FOUND\nIDC0551I ** ENTRY {d} NOT FOUND\nIDC0001I FUNCTION COMPLETED, HIGHEST CONDITION CODE WAS 8"
        return (f"NONVSAM ------- {d}\n   IN-CAT --- CATALOG.Z31.MASTER\n   HISTORY\n     CREATION--------2026.012  EXPIRATION------0000.000\n"
                f"   SMSDATA\n     STORAGECLASS ---SCSYSTEM\n   VOLUMES\n     VOLSER------------{KNOWN_DSN[d]}\nIDC0001I FUNCTION COMPLETED, HIGHEST CONDITION CODE WAS 0")
    if M(r"^LISTCAT LEVEL\('?([^')]+)'?\)$"):
        h = st["m"].group(1); r = [d for d in KNOWN_DSN if d.startswith(h)]
        return "\n".join(f"NONVSAM ------- {d}" for d in r) + "\nIDC0001I FUNCTION COMPLETED, HIGHEST CONDITION CODE WAS 0" if r else "IDC3012I NO ENTRIES FOUND"
    if M(r"^LISTUSER (\w+)$"):
        u = st["m"].group(1)
        return (f"USER={u}  NAME=JANE SYSPROG  OWNER=SYSADM  CREATED=26.100\n DEFAULT-GROUP=SYSPROG  PASSDATE=26.281  PASS-INTERVAL=90\n"
                " ATTRIBUTES=SPECIAL\n GROUP=SYSPROG AUTH=USE\n GROUP=DEVGRP  AUTH=USE")
    if M(r"^LISTDSD DATASET\('?([^')]+)'?\)( ALL)?$"):
        return (f"INFORMATION FOR DATASET {st['m'].group(1)} (G)\n LEVEL OWNER   UNIVERSAL ACCESS\n 00    USER01  NONE\n AUDITING: FAILURES(READ)\n ID      ACCESS\n DEVGRP  READ")
    if M(r"^(ADDUSER|ALTUSER|CONNECT|ADDSD|PERMIT|RDEFINE)\b"): return f"{st['m'].group(1)} processed (simulated RACF)"
    if M(r"^SETROPTS RACLIST\((\w+)\) REFRESH$"): return f"ICH14... RACLIST for {st['m'].group(1)} refreshed - profile changes now active (simulated)"
    if M(r"^SUBMIT (\w+)$"):
        n = st["m"].group(1)
        return f"JOB00123 SUBMITTED\n{JCL_OUT[n]}" if n in JCL_OUT else f"IKJ56500I COMMAND {n} NOT FOUND. Try: " + ", ".join(JCL_OUT)
    # ---- SDSF
    if M(r"^SDSF DA$"):
        return "NP JOBNAME  JobID    Owner   C  DP  Real\n" + "\n".join(f"   {j['name']:<7} {k}  USER01  {j['c']}  NS  1200" for k, j in s.jobs.items() if j["q"] == "EXECUTION")
    if M(r"^SDSF ST$"):
        return "NP JOBNAME  JobID    Owner   Queue      C\n" + "\n".join(f"   {j['name']:<7} {k}  USER01  {j['q']:<10} {j['c']}{' (HELD)' if j['held'] else ''}" for k, j in s.jobs.items())
    if M(r"^SDSF LOG$"): return f"N 4000000 SYSA {DATE} {t} JOB01234 IEF450I MYJOB1 STEP1 - ABEND=S0C7 U0000 REASON=00000007\nN 4000000 SYSA {DATE} {t} JOB01234 IEF404I MYJOB1 - ENDED"
    if M(r"^SDSF INIT$"): return execute(s, "$DI")
    # ---- abends, dumps, perf
    if M(r"^(ABEND |CODE )?(S[0-9A-F]{3})$"):
        a = st["m"].group(2); return f"{a}: {ABENDS[a]}" if a in ABENDS else f"{a}: look up in the IBM 'MVS System Codes' manual."
    if M(r"^STATUS FAILDATA$"): return "IPCS STATUS FAILDATA\n COMPONENT: (from dump)  ABEND=S0C7 REASON=00000007  PSW=078D1000 80AF3C2A (simulated)"
    if M(r"^STATUS$"): return "IPCS STATUS\n SYSTEM: SYSA  DUMP TYPE: SVC DUMP  ASID 0034 (simulated)"
    if M(r"^RMF$"):
        return ("Service Class  Imp Goal       Actual  PI\nBATCHHI         3  Vel 60%    64%     0.94\nCICSHI          1  RT 90%/0.5 91%     0.99\n"
                "STCHIGH         1  Vel 70%    68%     1.03  <- missing goal\nTSOPRD          2  RT 85%/1.0 88%     0.97\nBATCHLO         5  Disc       --      --")
    # ---- SMP/E
    sm = s.smpe
    if M(r"^RECEIVE SELECT\((\w+)\)\.?$"):
        sm["received"].add(st["m"].group(1)); return "GIM20502I RECEIVE PROCESSING IS COMPLETE. THE HIGHEST RETURN CODE WAS 0000."
    if M(r"^(APPLY|ACCEPT) SELECT\((\w+)\)( CHECK)?( GROUPEXTEND)?\.?$"):
        a, p, chk = st["m"].group(1), st["m"].group(2), bool(st["m"].group(3))
        if p not in sm["received"]: return f"ERROR: {p} has not been RECEIVED (RC=8). Run RECEIVE first."
        if a == "ACCEPT" and p not in sm["applied"]: return f"ERROR: {p} must be APPLIED before ACCEPT (RC=8)."
        if chk: return f"{a} CHECK for {p}: would succeed. No changes made. HIGHEST RETURN CODE WAS 0000."
        if a == "APPLY":
            sm["applied"].add(p); return f"GIM43401I APPLY PROCESSING FOR {p} WAS SUCCESSFUL.\nGIM20501I APPLY PROCESSING IS COMPLETE. THE HIGHEST RETURN CODE WAS 0000."
        sm["accepted"].add(p); return f"ACCEPT PROCESSING FOR {p} COMPLETE. Change is now permanent (RC 0000)."
    if M(r"^RESTORE SELECT\((\w+)\)\.?$"):
        p = st["m"].group(1)
        if p in sm["accepted"]: return f"ERROR: {p} is ACCEPTED - cannot RESTORE (RC=8). ACCEPT is permanent."
        if p not in sm["applied"]: return f"ERROR: {p} is not applied (RC=8)."
        sm["applied"].discard(p); return f"RESTORE of {p} complete (RC 0000)."
    if M(r"^REJECT SELECT\((\w+)\)\.?$"):
        sm["received"].discard(st["m"].group(1)); return "REJECT complete (RC 0000)."
    if M(r"^LIST (SYSMODS|PTFS)$"):
        al = sm["received"] | sm["applied"] | sm["accepted"]
        return "\n".join(f"{p}  RECEIVED{' APPLIED' if p in sm['applied'] else ''}{' ACCEPTED' if p in sm['accepted'] else ''}" for p in sorted(al)) or "No SYSMODs in the simulated CSI yet. Try RECEIVE SELECT(UK12345)."
    if M(r"^REPORT (ERRSYSMODS|MISSINGFIX)$"): return f"{st['m'].group(1)} report: no error holds affect installed SYSMODs (simulated). RC 0000."
    # ---- fallback with fuzzy suggestion (simple ML-style approximate matching)
    sug = difflib.get_close_matches(c, CATALOG, n=3, cutoff=0.45)
    return f"IEE305I {c.split()[0]} COMMAND INVALID or not supported in this simulator" + (("\nDid you mean:  " + "   |   ".join(sug)) if sug else "\nType HELP for the list.")
