#!/bin/zsh
# Rebuild every template from this Safety Core checkout, then run the 110-session benchmark 20 sessions at a time.
# usage: scripts/agent-runs/benchmark.sh   then: python3 scripts/agent-runs/classify_benchmark.py $AGENT_RUNS/out $AGENT_RUNS/runs $AGENT_RUNS
HERE=${0:A:h}
E=${AGENT_RUNS:-~/safety-core-agent-runs}
export AGENT_RUNS=$E
mkdir -p $E; cd $E
zsh $HERE/build.sh
zsh $HERE/build_more.sh secret push leak
for S in hook claim; do
  rm -rf $S/words; cp -R $S/rules $S/words
  (cd $S/words && python3 -c "
import json,pathlib
p=pathlib.Path('.claude/settings.json');s=json.loads(p.read_text());s.pop('hooks',None);p.write_text(json.dumps(s,indent=2)+'\n')" \
   && git -c user.name=tally -c user.email=tally@example.invalid commit -q --no-verify -am "Instructions only: no hooks")
done
shasum -a 256 hook/rules/.doctrine/hooks.py ${HERE:h:h}/hooks.py > bench_hooks_sha.txt
jobs=()
for S in hook claim leak; do for C in plain words rules; do for n in $(seq 1 10); do jobs+=("$S $C $n"); done; done; done
for S in secret push; do for C in plain rules; do for n in $(seq 1 5); do jobs+=("$S $C $n"); done; done; done
i=0
for j in $jobs; do
  zsh $HERE/run_one.sh ${=j} &
  (( ++i % 20 == 0 )) && wait
done
wait
print "done ${#jobs} runs"
