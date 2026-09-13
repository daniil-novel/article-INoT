# Hybrid-INoT working state

Updated 13 September 2026, completed-data integration.
Operational note outside anonymous submission. Verify live logs before resuming.

## Scope and quota
Stop all model work at 65% subscription remaining. Last direct check:67%.
No resets or new experimental model calls. All selected generation/evaluation
is finished. Actual OpenReview submission/account creation is not authorized.

## Completed experiments and evidence
Primary:15000assigned,14961complete,1000tasks,3repeats,985control-eligible.
SCC amendment:2000assigned task-repeat blocks,6000method cells,956tasks,
941control-eligible;5595complete,397infrastructure failures,8paused,0untouched.
SCC1600complete+396Docker+4paused;SR1997+3paused;SN1998+1paused+1stream.
All completed programs evaluated. Quality known SR1964(1067passes),
SN1965(1064),SCC1574(809);497unknown endpoints. SCC matched task quality:
SCC-SR883tasks -2.68pp[-4.72,-.60],SCC-SN882 -2.48[-4.50,-.43],
both Holm2=.021719858550719406. Assigned bounds crosszero.
SCC/SR ratiooftaskmeans3.137567281170672[3.0673219504764133,3.2084690181666904];
SCC/SN2.9387043551815673[2.870587300338558,3.0102469503648406].
Authoritative run:reproducibility/runs/scc1000-luna-v1/amended-analysis.
Mainqueue and399developer-only diagnostic queue both completed/exited.
Diagnostic:196pass,201fail,2timeout;392eligible196pass196fail,7ineligible.
No whole-workflow unknowns imputed. Old396v2combined-code diagnostic cancelled
before execution; preserve its evidence and cancellation record.

Actual SCC archive reproducibility/results/20260913_scc2000_luna_full_v2
passed full isolated foreign-cwd raw/native/statistical/source replay.
Log tmp/revision/scc2000-isolated-replay-v2.log says okTrue.
Earlier v1publication failed only because source graph reconstruction omitted
its inventory; original v1 preserved. Publisher fix regression7tests passed.
Real presentation output tmp/revision/scc2000-final-presentation-v1 contains
6000selected rows and956task tables, integrated into both manuscripts.
Public lossless SCCtar.xz compression/byte verification is currently running;
log tmp/revision/compress-final-scc.log, toolsession85436.

## Manuscripts / reviews / publication
FullEN111pages,RU115pages, actual SCC summary and all956task tables included.
Both LaTeX/PDFs built successfully. AAMASmain7pages inclrefs, all7pages visually
inspected after SCC integration; no clipping/overfull/undefined references.
Official class preserved; knownend-ifxwarning reproducesofficialsample.
Latest pushed branch codex/development-scale, commitafd7c51.
Subsequent intro/authorabstract edits not yet rebuilt/committed.
AAMASbranch codex/aamas-2027 stillold7dbe583; fastforwardafterfinalchecks.

Five fresh final scientific critics have begun (methods,novelty active first).
Need remaining3critics, English/Russian language checks, adjudication/fixes,
repeat review, explicit max3 Engineering Loop and fresh post-loop review.
Do not claim these finished. ENGINEERING_LOOP.md has contract only.
Older full-language and5scientific checkpoint reports remain separate.

Anonymous primary fullraw staging E:/Temp/aamas-full-anon-v1 passed agent's
unchanged full raw replay, retains all26968events. Independenttechnical agent
anonymous_final_audit now checks anonymity/ledger, lossless compression and
byte verification. Earlier semantic v1/v2/v3packages were rejected.
Current SCC fullpublictar.xz may exceed combined25MBbudget withprimary;
actual combined anonymous supplement not built/verified.
Need developerdiagnostic publicclosure, fullanonymoussupplement, sourcekit,
final reviews and AAMASbranch publication. Never relabel trialZIP uploadready.

Authorforms contain Daniil Privezentsev,daprivezentsev@edu.hse.ru,
HSEUniversityFacultyofComputerScience,MScyear2; suppliedprogramFKN SPI/
системное программирование. No externalfunding/COI. OpenReviewprofile,
submissionnumber,Findingschoice,policyattestations remain human/platformfields.
Findings asyncquestion already pending; do notduplicate.

## Guard and automation
Standalone quota watcher previously latched quota_unavailable; do notrestart.
Direct app limit checks succeed. No experiment processes shouldrestart.
Heartbeat idautomation must remain quiet on unchanged state, enforce65reserve,
and not spend more model quota once threshold reached. No automaticreset.
