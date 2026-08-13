import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createTool } from "@mastra/core/tools";
import { MCPClient } from "@mastra/mcp";
import { z } from "zod";
import { addStep, listTodos, listGoalAndSteps, completeTodo } from "./board.ts";

export const WORKSPACE = join(dirname(fileURLToPath(import.meta.url)), "workspace");

const taskIdEnv = process.env.TASK_ID ? Number(process.env.TASK_ID) : null;

export const showTodos = createTool({
  id: "show_todos",
  description:
    "List todos for your claimed goal only (Day 5) or the whole board (standalone).",
  inputSchema: z.object({}),
  execute: async () => {
    const args = process.argv.slice(2);
    const tid = args.length >= 2 ? Number(args[0]) : taskIdEnv;
    if (tid != null && !Number.isNaN(tid)) {
      return { todos: listGoalAndSteps(tid) };
    }
    return { todos: listTodos() };
  },
});

export const planSteps = createTool({
  id: "plan_steps",
  description: "Break a goal into ordered steps on the board.",
  inputSchema: z.object({ goalId: z.number(), steps: z.array(z.string()) }),
  execute: async ({ goalId, steps }) => ({
    goalId,
    stepIds: steps.map((s: string) => addStep(goalId, s)),
  }),
});

export const completeTask = createTool({
  id: "complete_task",
  description: "Mark a todo done and record a short result.",
  inputSchema: z.object({ taskId: z.number(), result: z.string() }),
  execute: async ({ taskId, result }) => {
    completeTodo(taskId, result);
    return { taskId, status: "done" };
  },
});

export const boardTools = { showTodos, planSteps, completeTask };

export function makeFilesystem(dir = WORKSPACE): MCPClient {
  return new MCPClient({
    servers: {
      filesystem: {
        command: "npx",
        args: ["-y", "@modelcontextprotocol/server-filesystem", dir],
        stderr: "ignore",
        cwd: dir,
      },
    },
  });
}
