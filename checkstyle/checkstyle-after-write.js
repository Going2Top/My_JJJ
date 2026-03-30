import { spawn } from "node:child_process"
import path from "node:path"

function runPowerShell(scriptPath, cwd) {
  return new Promise((resolve) => {
    const child = spawn(
      "powershell.exe",
      ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", scriptPath],
      { cwd, shell: false },
    )

    let stdout = ""
    let stderr = ""

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString()
    })

    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString()
    })

    child.on("close", (code) => {
      resolve({ code, stdout, stderr })
    })
  })
}

export const CheckstyleAfterWritePlugin = async ({ client, directory, worktree }) => {
  const projectRoot = worktree || directory
  const scriptPath = path.join(projectRoot, ".opencode", "checkstyle", "checkstyle-changed.ps1")
  const writeTools = new Set(["edit", "write", "patch", "multiedit"])
  let running = false
  let queued = false
  let lastFailure = ""

  async function flush() {
    do {
      queued = false

      const result = await runPowerShell(scriptPath, projectRoot)
      const output = [result.stdout.trim(), result.stderr.trim()].filter(Boolean).join("\n")

      if (result.code === 0) {
        lastFailure = ""
        if (output) {
          await client.app.log({
            body: {
              service: "checkstyle-after-write",
              level: "info",
              message: "Checkstyle run completed after a write tool.",
              extra: { output },
            },
          })
        }
        continue
      }

      if (output !== lastFailure) {
        lastFailure = output
        await client.app.log({
          body: {
            service: "checkstyle-after-write",
            level: "warn",
            message: "Checkstyle run failed after a write tool.",
            extra: { output, exitCode: result.code },
          },
        })
      }
    } while (queued)
  }

  return {
    "tool.execute.after": async (input) => {
      if (!writeTools.has(input.tool)) {
        return
      }

      if (running) {
        queued = true
        return
      }

      running = true
      try {
        await flush()
      } finally {
        running = false
      }
    },
  }
}
