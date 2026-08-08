---
title: Stop Writing Log Parsers
date: 2026-06-02
tags: [python, tooling, logging]
draft: false
---

I have written the same log parser at least six times. Different jobs, different
formats, same script: read lines, run a regex, pull out a timestamp and a level and
a message, count things, print a summary. Every version worked. Every version was
thrown away within a year because the log format changed.

## The actual problem

The parser is never the hard part. The hard part is that the log was designed to be
read by a human scrolling a terminal, and I keep trying to read it with a machine.
A line like this is easy to skim and genuinely annoying to parse:

    2026-06-02 09:14:22 WARN  retry 3/5 for job 41ab (timeout after 30.0s)

Everything I care about is in there — the job id, the attempt number, the timeout —
and every one of them is embedded in prose. Extracting `3/5` requires a regex that
breaks the moment somebody rewrites the message to say "attempt 3 of 5".

## Structured logging is the boring fix

The fix is to log the fields as fields. With `loguru` that is close to free, because
`bind()` attaches structured context that a sink can serialize:

```python
from loguru import logger

logger.add('app.jsonl', serialize=True, level='INFO')

job_log = logger.bind(job_id='41ab')
job_log.warning('retry scheduled', attempt=3, max_attempts=5, timeout_s=30.0)
```

Now the human-readable sink still prints a sentence, and the JSON sink emits a record
with `job_id`, `attempt`, `max_attempts` and `timeout_s` as real keys. The parser
becomes `json.loads`, which is a parser I will never have to rewrite.

## What changed in practice

Three things got noticeably better once I stopped parsing prose:

1. Message wording became free to change. Rewording a log line used to be a
   breaking change to my tooling; now it is a typo fix.
2. Analysis moved from regex to filtering. "Show me every job that retried more
   than twice" is a one-line comprehension instead of a parsing exercise.
3. New fields cost nothing. Adding `queue_depth` to a log call does not require
   touching anything downstream.

The cost is that you have to decide, at the call site, what the interesting fields
are. That is real work, but it is work you were doing anyway — you were just doing
it later, in a regex, with less information.

If you are staring at a log file wondering how to parse it, the better question is
usually whether you can change how it is written.
