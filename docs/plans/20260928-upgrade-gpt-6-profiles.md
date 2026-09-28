# Upgrade Sol and Luna agent profiles to GPT-6

## Goal

Ship a PR in which pstack's active Sol and Luna profiles use GPT-6, Terra profiles keep `gpt-5.6-terra`, the routing guide matches the shipped TOMLs, and future upstream syncs preserve this choice.

## Scope and decision

The repository has five Sol or Luna agent TOMLs, four Terra TOMLs, one routing table, and a converter with model replacements. This is a bounded configuration change with no new production dependency.

The [OpenAI model catalog](https://developers.openai.com/api/docs/models) lists GPT-6 Astra, Sol, and Luna. The user directed us to keep GPT-5.6 Terra until GPT-6 Terra is released. Map existing Sol profiles to `gpt-6-sol` and Luna profiles to `gpt-6-luna`. Keep every Terra profile and converter target on `gpt-5.6-terra`, including the upstream Claude Opus mapping. Preserve the current three-model Arena and Interrogate routing.

Keep `gpt-5.6-sol-max` as a converter input and map it to `gpt-6-sol`. Add direct conversion for GPT-5.6 Sol and Luna after that more specific rule. The conversion data is an ordered list of source and destination string pairs. Historical port notes stay intact.

## Definition of done

- All twelve shipped TOMLs parse. Sol and Luna profiles select GPT-6 models with supported reasoning effort, while all four Terra profiles still select `gpt-5.6-terra`.
- The routing guide matches the TOMLs and retains Terra as a distinct model in the current composition.
- The converter maps representative Sol and Luna source tokens to GPT-6 and keeps both direct and upstream Terra inputs on GPT-5.6 Terra.
- A temporary installation copies the expected mixed model set. Plugin validation and the focused converter test pass.
- The PR contains only this change and the plan. The unrelated mode change to `scripts/install-agents.sh` stays out.

## Workflow checklist

- [x] Read the Principles section of the **poteto-mode** skill.
- [x] Phase A: Frame.
- [x] Phase B: Design the workflow.
- [x] Phase C: Run the loop.
- [x] Phase D: Keep the audit trail.
- [ ] Phase E: Verify and hand back.

## Execution units after approval

- [x] Capture a pre-change model inventory and a failing converter behavior check in a rerunnable standard-library test.
- [x] Update the converter's ordered replacements and focused test for the corrected model mapping.
- [x] Update five Sol and Luna TOMLs. Preserve four Terra TOMLs. Parse and install them into a temporary `CODEX_HOME` to inspect the copies.
- [x] Update model routing. Verify that all profile references resolve and the routing table matches the TOMLs.
- [x] Run the full artifact checks, inspect the diff, and review the local decision trail against evidence.
- [ ] Commit with a Conventional Commit message, push the isolated branch, and open a ready PR on the fork with this plan and current checklist in an `Implementation Plan` details block.

## Skill edit gate

Skipped. The user correction removed the planned `SKILL.md` edit. The setup skill already requires model-named profiles to stay on their named family.

## Rigor and tradeoffs

Use one PR and small verified units. GPT-5.6 Terra remains in use by explicit request, so this is a mixed-family configuration until a Terra successor exists. A local decision trail at `.audit/20260928-upgrade-gpt-6-profiles.tsv` records the initial mapping and the user correction. The focused test and plan carry the review evidence in the PR.

## Progress

The pre-change check failed as expected for seven representative model inputs. The user directed us to keep Terra on GPT-5.6. The converter test now passes with Terra preserved. The four Terra TOMLs and historical docs match their original state.

A second temporary installation copied the mixed model set. Each Terra TOML is byte-for-byte equal to its version on `main`.

The routing table matches all twelve named profiles. Arena and Interrogate still use Sol, Terra, and Luna for ordinary work.

## Verification

- `python3 -m unittest discover -v` passed two tests. The tests cover nine converter inputs and copy all twelve profiles through `scripts/install-agents.sh` into a temporary Codex home.
- `uv run --with pyyaml python ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py plugins/pstack-codex` passed.
- `git diff --check` passed. A diff against `main` showed no change to the four Terra TOMLs. A search found no active GPT-5.6 Sol or Luna ID under `plugins/pstack-codex`.

An independent reviewer rechecked the decision trail and diff. The reviewer found no remaining verification or scope issue after the discoverable tests and installation check were added.
