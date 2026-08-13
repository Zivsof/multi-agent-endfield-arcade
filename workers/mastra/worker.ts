/**
 * Mastra worker for Endfield arcade Day-5 mode.
 */

import "./env.ts";
import { join, dirname } from "node:path";
import { mkdirSync, rmSync, existsSync, readFileSync } from "node:fs";
import { Agent } from "@mastra/core/agent";
import { boardTools, makeFilesystem, WORKSPACE } from "./tools.ts";
import { resetBoard, addGoal, claimTodo, showBoard, BOARD_PATH } from "./board.ts";

const args = process.argv.slice(2);
const TASK_ID = args.length >= 2 ? Number(args[0]) : null;
const WORK_DIR = TASK_ID === null ? WORKSPACE : dirname(BOARD_PATH);

const GOAL =
  "Read notes.txt, translate its contents into natural Spanish, and write the Spanish to spanish.txt.";

const INSTRUCTIONS = `
You are a careful worker with a shared todo board and a set of file tools.
When working a claimed task id, call show_todos to see ONLY that goal and its steps — ignore other builders' work.
Take the pending goal and see it through. Plan steps on the board, use file tools, mark done, close the goal.
`;

function seed(): number {
  mkdirSync(WORKSPACE, { recursive: true });
  rmSync(join(WORKSPACE, "spanish.txt"), { force: true });
  resetBoard();
  const goalId = addGoal(GOAL);
  claimTodo(goalId);
  return goalId;
}

let message: string;
if (TASK_ID === null) {
  const goalId = seed();
  console.log(`Seeded goal ${goalId}: ${GOAL}\n`);
  message = "Please work the pending goal on the board.";
} else {
  claimTodo(TASK_ID);
  message =
    `You have claimed task #${TASK_ID} on the shared board. Work only that task and its steps. ` +
    `When the work is built and checked, mark task #${TASK_ID} itself done with complete_task, then stop.`;
}

const filesystem = makeFilesystem(WORK_DIR);
const worker = new Agent({
  id: "worker",
  name: "Worker",
  instructions: INSTRUCTIONS,
  model: "openai/" + (process.env.WORKER_MODEL ?? "gpt-5.4-mini"),
  tools: { ...boardTools, ...(await filesystem.listTools()) },
});

await worker.generate(message, {
  maxSteps: 25,
  onStepFinish: (step: { toolCalls?: { payload: { toolName: string; args?: unknown } }[] }) => {
    if (TASK_ID !== null) return;
    for (const call of step.toolCalls ?? []) {
      console.log(`  called ${call.payload.toolName}(${JSON.stringify(call.payload.args)})`);
    }
  },
});
await filesystem.disconnect();

if (TASK_ID === null) {
  console.log("\nBoard after the run:");
  showBoard();
  const spanish = join(WORKSPACE, "spanish.txt");
  if (existsSync(spanish)) {
    console.log("\nspanish.txt:\n" + readFileSync(spanish, "utf-8"));
  }
}

process.exit(0);
