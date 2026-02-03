# Plan

# 1.
Make a an agent that runs the daily task prompt:
1.Needs to call anthropic APi
2.Run the pre made daily task prompt but also views the log so it doesnt repeat
3.Return the result to a local file where it will be pushed to github
4.needs to also create a portfolio log in this form:
# Daily AI Challenge – [Date]

**Domain:** [e.g., Finance, Operations]
**Tool Focus:** [e.g., Claude Code, Mixed Tools]
**Time Box:** [e.g., 90 minutes]
**Status:** [Pending / Completed / Partial]

## Challenge Summary
[Brief description]

## Skills Trained
- [Skill 1]
- [Skill 2]
- [Skill 3]

## Deliverables
- [Deliverable 1]
- [Deliverable 2]


# Realisaions

In the process of creating i have realised adding a feature to allow it to output dtat files will make the challenges produced alot better.

I also realise that using windows task schedular would require my pc to be on for the automation to run so instead im setting up a github actions workflow


