# `ask_person`: Ask the person

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: (the AI app's question form: MCP elicitation). Category: Help. Read-only. Needs nothing.

## What it does

Ask the person questions as a form in the AI app (MCP elicitation), where the app can show one (Claude Code in a terminal does): the answer is what they filled in, or that they declined. Where the app cannot (Claude Desktop, Gemini CLI, the chat panel, the command line, or a headless server), it answers at once that you should ask in your reply: then ask every question in one message, with its default, and wait. Use it for the questions plan_approach gives; asking in your reply always works, so never depend on it. Read-only.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `questions` (required) | array of objects |  |  | at least 1 item(s), at most 8 item(s) | the questions, most important first |
| `message` | string |  |  |  | one line above the questions (what they are for) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Called without arguments, the arguments are refused before anything runs: `Not done: questions is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: where the app cannot show a form, the answer says to ask in the reply

Starting from Fission 180 with no design open.

The call:

```json
{"tool": "ask_person", "args": {"message": "Before I convert the mesh:", "questions": [{"question": "A solid you can cut and print, or an editable timeline?", "choices": ["a solid", "an editable timeline"], "default": "a solid"}]}}
```

The answer:

```text
This AI app cannot show questions from Fission 180 itself (MCP elicitation is off or not supported here): ask the questions in your reply, all in one message with their defaults, and wait for the answer.
```

## More argument examples

- one question with two choices:
  `{"message": "Before I convert Relic:", "questions": [{"question": "A solid you can cut and print, or an editable timeline?", "choices": ["a solid", "an editable timeline"], "default": "a solid"}]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
