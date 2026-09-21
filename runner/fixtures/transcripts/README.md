# Recorded transcripts

Output a model actually produced, kept verbatim as calibration fixtures for
the powered ablation's probes. The selftest asserts that each probe reaches
the same verdict on these as the run did.

They exist because calibrating a probe against invented phrasings is not
enough. On 2026-09-21 the seven probes were rewritten and calibrated against
transcripts written by hand, which is better than fixtures written in a
grader's own words and still not the same as what a model writes. The first
pilot to return real answers failed one of them: the reply quoted the
collection identifier as `LLC0090` where the probe asked for `llc90`, and
offered a "native path" where the probe demanded a "native grid". The rubric
judge passed that answer and the programmatic probe did not, so a correct
answer was recorded as a failure.

## These files are evidence, so nothing edits them

They are copied out of a run unchanged and must stay that way. Reformatting
one, or correcting its prose to the house style, would make it a paraphrase
and it would stop testing what it exists to test. They do contain dashes and
wording the repositories' own prose rules forbid, which is the point: the
probes have to accept the language a model writes, not the language we would
have written.

No repository gate scans this directory for wording, and none should. If these
fixtures are ever copied into a repository whose gate does scan prose, that
gate needs an exclusion for this directory rather than an edit to the files.

## Naming

`<case id>.<arm>-trial<n>.<expected>.txt`, where `<expected>` is `pass` or
`fail`: the verdict the probe for that case must reach. `selftest.py` maps the
case id to its probe and checks every file here.

To add one, copy a trial's `.txt` out of a run's transcripts directory without
changing a byte, name it for the case and the verdict the run recorded, and
check the selftest still passes.
