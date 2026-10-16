"""Course content: modules -> concept + guided command steps; roadmap; quiz."""

def S(text, *cmds): return {"text": text, "try": list(cmds)}

MODULES = [
 dict(id=1, title="Architecture: address spaces & virtual storage", phase=1,
  concept="""Every job, started task, TSO user and system component gets its own **private virtual address space** (unique **ASID**); common areas (**Nucleus, PLPA/LPA, CSA, SQA**) are shared.
- **TCB** = unit of work for user programs; **SRB** = lighter system work.
- Addressing: 24-bit (16 MB *line*), 31-bit (2 GB *bar*), 64-bit.""",
  steps=[S("List active address spaces. Row 1 gives counts; each row shows jobname, stepname, procstep and flags (NSW = non-swappable).", "D A,L"),
         S("Check one address space by name.", "D A,JES2"),
         S("See central storage and processors.", "D M=STOR", "D M=CPU")]),
 dict(id=2, title="IPL & system initialization", phase=1,
  concept="""IPL loads the nucleus from SYSRES, then reads PARMLIB. **LOAD parm** (ddddxxMN) -> **LOADxx** -> IEASYSxx/IEASYMxx -> **NIP** -> master scheduler (COMMNDxx, IEFSSNxx) -> **JES2**.
`CLPA` rebuilds the pageable link pack area; skip it on routine re-IPLs. `WARM/COLD/FORMAT` at $HASP426 decide how JES2 recovers spool.""",
  steps=[S("Replay an IPL. Type IPL, then reply to the IEA101A prompt.", "IPL"),
         S("Answer the system-parameter prompt with CLPA.", "R 00,CLPA"),
         S("Answer the JES2 start prompt (NOREQ = warm).", "R 01,NOREQ"),
         S("After IPL, check what was used.", "D IPLINFO")]),
 dict(id=3, title="Operator console commands", phase=1,
  concept="""**D** display, **V** vary, **SET/SETPROG** change config, **S/P/C/F** start/stop/cancel/modify, **R** reply.
Safety: spell out the target, `D A,jobname` before `P`, prefer **P** over **C** for production, run `D PARMLIB`/`D PROG,*` before and after changes.""",
  steps=[S("Run the five first-look commands. Start with PARMLIB.", "D PARMLIB"),
         S("Check GRS contention and outstanding replies.", "D GRS,C", "D R,L"),
         S("Vary a device offline then online.", "V 0A82,OFFLINE", "V 0A82,ONLINE"),
         S("Start and stop a started task.", "S MYPROC", "P MYPROC"),
         S("Cancel a job (compare with P: C forces it).", "C MYJOB3")]),
 dict(id=4, title="Datasets, DASD, VTOC & catalogs", phase=2,
  concept="""Datasets live on volumes (**VTOC** lists them) and are found by name via **ICF catalogs** (master catalog + user catalogs via aliases).
Attributes: DSORG, RECFM, LRECL, BLKSIZE, DSNTYPE. **PDS** needs compress; **PDSE** reuses space, needs SMS.""",
  steps=[S("Find which catalog and volume hold SYS1.PARMLIB.", "LISTCAT ENTRIES('SYS1.PARMLIB') ALL"),
         S("List everything under a high-level qualifier.", "LISTCAT LEVEL(SYS1.PARMLIB)"),
         S("Try a dataset that does not exist and read the IDC messages.", "LISTCAT ENTRIES('NO.SUCH.DATA') ALL")]),
 dict(id=5, title="JCL & utilities", phase=2,
  concept="""Six utilities cover most tasks: **IEFBR14** (allocate/delete), **IEBGENER** (copy sequential), **IEBCOPY** (PDS/PDSE), **IDCAMS** (VSAM/catalog), **ADRDSSU** (dump/restore), **IEHLIST** (VTOC).
Always read the return code and `IEF285I` lines.""",
  steps=[S("Submit the IEFBR14 allocation job.", "SUBMIT ALLOC"),
         S("Copy it with IEBGENER, then compress a PDS.", "SUBMIT COPY", "SUBMIT COMPRESS"),
         S("Define a VSAM KSDS, back up with ADRDSSU, list the VTOC.", "SUBMIT DEFVSAM", "SUBMIT DUMP", "SUBMIT LISTVTOC")]),
 dict(id=6, title="PARMLIB, LPA, link list & APF", phase=3,
  concept="""Search order: job pack, STEPLIB/JOBLIB, **LPA**, **link list**. **APF** authorization needs *both* AC(1) and an authorized library.
`PROGxx` = permanent; `SETPROG` = dynamic. After link-list changes: `F LLA,REFRESH`. Never authorize a library ordinary users can write to.""",
  steps=[S("Display the current APF list.", "D PROG,APF"),
         S("Add a library dynamically, then confirm.", "SETPROG APF,ADD,DSNAME=USER.TEST.AUTHLIB,VOLUME=USRP01", "D PROG,APF,DSNAME=USER.TEST.AUTHLIB"),
         S("Define, extend and activate a new link list, then refresh LLA.", "SETPROG LNKLST,DEFINE,NAME=LNKLST02,COPYFROM=CURRENT",
           "SETPROG LNKLST,ADD,NAME=LNKLST02,DSNAME=USER.UTIL.LOAD", "SETPROG LNKLST,ACTIVATE,NAME=LNKLST02", "F LLA,REFRESH"),
         S("Verify the link list.", "D PROG,LNKLST")]),
 dict(id=7, title="JES2 & SDSF", phase=3,
  concept="""Job flow: **input -> conversion -> queued -> execution -> output -> purge**. Key objects: spool, checkpoint, initiators, classes.
SDSF line commands: S show, H hold, A release, C cancel, P purge. Panels: DA, ST, LOG, INIT.""",
  steps=[S("Look at job status (SDSF ST).", "SDSF ST"),
         S("Display, hold and release a job with JES2 commands.", "$DJ1234", "$HJ1234", "$AJ1234"),
         S("Look at the initiators and change classes.", "$DI", "$TI3,CLASS=AB"),
         S("Read the SYSLOG.", "SDSF LOG")]),
 dict(id=8, title="SMP/E: install & maintain software", phase=4,
  concept="""Flow: **RECEIVE -> APPLY CHECK -> APPLY -> (test) -> ACCEPT**. Zones: GLOBAL, TARGET, DLIB; state lives in the **CSI**.
RESTORE works only before ACCEPT; **ACCEPT is permanent**. Read HOLDDATA first.""",
  steps=[S("RECEIVE the PTF.", "RECEIVE SELECT(UK12345)"),
         S("Test with APPLY CHECK, then APPLY for real.", "APPLY SELECT(UK12345) CHECK", "APPLY SELECT(UK12345)"),
         S("Try ACCEPT, or back it out with RESTORE (before ACCEPT only).", "ACCEPT SELECT(UK12345)", "RESTORE SELECT(UK12345)"),
         S("List what is installed.", "LIST SYSMODS")]),
 dict(id=9, title="Security with RACF", phase=4,
  concept="""RACF = users, groups, profiles, classes; access NONE..ALTER. Use **UACC(NONE)** + explicit PERMITs for groups. After changing a RACLISTed class: `SETROPTS RACLIST(class) REFRESH`.
`ICH408I` shows who tried what and why it failed; **S913** is the same from the job side.""",
  steps=[S("Inspect a user.", "LISTUSER USER01"),
         S("Inspect a dataset profile.", "LISTDSD DATASET('USER01.TEST.**') ALL"),
         S("Create a profile and permit a group.", "ADDSD 'USER01.TEST.**' UACC(NONE)", "PERMIT 'USER01.TEST.**' ID(DEVGRP) ACCESS(READ)"),
         S("Refresh the in-memory class.", "SETROPTS RACLIST(FACILITY) REFRESH")]),
 dict(id=10, title="Problem determination: ABENDs & dumps", phase=5,
  concept="""Read in order: first error message, ABEND code + reason, then SYSLOG around the failure time.
S0C4/S0C7 = program faults; S806/S913/S878 = environment/setup. Dumps: SYSUDUMP (app), SYSMDUMP/SVC dump (IPCS), stand-alone (last resort).""",
  steps=[S("Look up S0C7, then S806, S913.", "ABEND S0C7", "ABEND S806", "ABEND S913"),
         S("Find the failure in the system log.", "SDSF LOG"),
         S("IPCS basics: STATUS then STATUS FAILDATA.", "STATUS", "STATUS FAILDATA")]),
 dict(id=11, title="WLM & performance", phase=5,
  concept="""WLM manages by **goals**: service classes, importance (1-5), goal type (response time, velocity, discretionary). **PI** = 1.0 goal met; >1.0 missing goal.
Tune: find highest PI + importance, check delay reasons, fix the resource, re-measure.""",
  steps=[S("View the RMF summary and find the class missing its goal.", "RMF"),
         S("Check contention that may explain delay.", "D GRS,C", "$DSPOOL")]),
 dict(id=12, title="JES2 in depth: spool, checkpoint, initiators", phase=6,
  concept="""JES2 stays healthy only if the **spool**, **checkpoint** and **initiators** do. Warm start keeps queues; never cold start without a plan.
Watch spool volumes above ~70-80%.""",
  steps=[S("Check spool usage.", "$DSPOOL"),
         S("Display the checkpoint definition.", "$DCKPTDEF"),
         S("A job will not start: check its class, then initiators.", "$DJ1237", "$DI"),
         S("Drain and restart an initiator.", "$PI3", "$SI3")]),
 dict(id=13, title="SMP/E in depth: HOLDDATA & maintenance cycle", phase=6,
  concept="""Relationships: **PRE, REQ, IFREQ, SUP, SUPING**. **ERROR** holds = known problem; **SYSTEM** holds = work for you (ACTION, DOC, IPL, EXIT, DDDEF). Use GROUPEXTEND; bypass holds only after doing the action.
Return codes: 0 ok, 4 warnings, 8 not processed, 12+ severe.""",
  steps=[S("Run the pre-apply reports.", "REPORT ERRSYSMODS", "REPORT MISSINGFIX"),
         S("RECEIVE, then APPLY CHECK with GROUPEXTEND.", "RECEIVE SELECT(UK99999)", "APPLY SELECT(UK99999) CHECK GROUPEXTEND"),
         S("Apply, then ACCEPT after the trial period.", "APPLY SELECT(UK99999)", "ACCEPT SELECT(UK99999)")]),
]

PHASES = {1: "Foundations", 2: "Data & Batch", 3: "System Configuration", 4: "Maintenance & Security", 5: "Diagnosis & Tuning", 6: "Deep Dives"}

ROADMAP = [
 ("Phase 1 - Foundations (weeks 1-2)", [1, 2, 3], "Understand address spaces, IPL and read-only console commands."),
 ("Phase 2 - Data & Batch (weeks 3-4)", [4, 5], "Catalogs, VTOC, JCL and the six utilities."),
 ("Phase 3 - System Configuration (weeks 5-6)", [6, 7], "PARMLIB, APF, link list, JES2/SDSF operations."),
 ("Phase 4 - Maintenance & Security (weeks 7-8)", [8, 9], "SMP/E install flow and RACF protection."),
 ("Phase 5 - Diagnosis & Tuning (weeks 9-10)", [10, 11], "Dumps, IPCS, SYSLOG, WLM and RMF."),
 ("Phase 6 - Deep Dives (weeks 11-12)", [12, 13], "JES2 recovery and full SMP/E maintenance cycles."),
]
NEXT_STEPS = ["Parallel Sysplex, coupling facility, GRS ring/star", "REXX and CLIST automation, system automation tools",
              "z/OSMF, z/OS UNIX System Services (OMVS) administration", "SMF/RMF reporting, capacity planning",
              "Subsystem sysprog: CICS, Db2, MQ", "Hands-on: IBM Z Xplore or a hobbyist emulator (see course notes labs)"]

def Q(m, q, a, *wrong): return dict(m=m, q=q, a=a, opts=[a, *wrong])
QUIZ = [
 Q(1, "What are the 16 MB line and the 2 GB bar?", "24-bit and 31-bit addressing limits", "Two CSA subpools", "Page dataset sizes", "JES2 spool limits"),
 Q(1, "What is an ASID?", "Address space identifier", "A storage class", "An access control ID", "A job step name"),
 Q(2, "Which member is read first at IPL to locate others?", "LOADxx", "IEASYSxx", "COMMNDxx", "PROGxx"),
 Q(2, "What does the CLPA reply do?", "Creates a new pageable link pack area", "Cold-starts JES2", "Clears the catalog", "Compresses PARMLIB"),
 Q(3, "Difference between P and C?", "P asks a task to stop cleanly; C forces cancellation", "P purges output; C changes class", "They are identical", "P pauses; C continues"),
 Q(5, "Which utility copies and compresses a PDS?", "IEBCOPY", "IEFBR14", "IEHLIST", "IDCAMS"),
 Q(4, "What is a VTOC?", "Volume table of contents listing datasets and extents", "A VSAM catalog", "A JES2 queue", "A RACF profile"),
 Q(4, "How do you find which catalog holds a dataset?", "LISTCAT ENTRIES('dsn') ALL", "D PARMLIB", "$DJ", "SETPROG APF"),
 Q(6, "What two conditions make a program APF-authorized?", "AC(1) link-edit and an APF-authorized library", "REGION=0M and CLASS=A", "UACC(ALTER) and SPECIAL", "LPA and CSA residency"),
 Q(8, "What are the three SMP/E zone types?", "GLOBAL, TARGET, DLIB", "PRE, REQ, SUP", "CSI, VTOC, VVDS", "LPA, CSA, SQA"),
 Q(8, "Why run APPLY with CHECK first?", "Verifies the install without changing the system", "It accepts the PTF", "It clears HOLDDATA", "It restarts JES2"),
 Q(9, "What does ICH408I tell you?", "A RACF authorization failure: who, what, access lacked", "An IPL parameter error", "A JES2 spool shortage", "An SMP/E return code"),
 Q(10, "What does S0C7 usually mean?", "Data exception: invalid numeric data", "Module not found", "Protection exception", "CPU time exceeded"),
 Q(11, "What does a PI above 1.0 mean in WLM?", "Service class is missing its goal", "Goal exceeded", "Class is discretionary", "System is idle"),
 Q(9, "After changing a RACLISTed class profile, what must you do?", "SETROPTS RACLIST(class) REFRESH", "F LLA,REFRESH", "SET PROG=01", "$PJES2"),
]
