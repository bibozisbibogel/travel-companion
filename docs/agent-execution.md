  _execute_queued_agents() method in the parallel executor:

  Purpose

  This method executes all queued agents with parallel coordination, managing dependencies, concurrency
  limits, and state updates throughout the execution lifecycle.

  Key Functionality

  1. State Management

  - Creates a deep copy of the initial state to track changes
  - Maintains agents_completed and agents_failed lists in the state for dependency tracking
  - Updates state as each agent completes successfully

  2. Main Execution Loop (lines 510-646)

  The method runs a continuous loop that:

  a) Processes Completed Tasks (lines 512-539)
  - Checks for any finished tasks in self.active_tasks
  - Extracts results and marks successful agents as completed
  - Updates the agents_completed list for dependency tracking

  b) Gets Next Agent (lines 542-586)
  - Pulls the next available agent from the priority queue
  - If no agent is available but tasks are running, waits for completion
  - Implements deadlock detection (lines 556-569) to prevent infinite loops

  c) Dependency Checking (lines 591-630)
  - Verifies if agent dependencies are satisfied before execution
  - Re-queues agents with unsatisfied dependencies (with lower priority)
  - Tracks retry counts to prevent infinite dependency loops
  - Fails agents after max dependency retries (2 attempts)

  d) Task Creation & Execution (lines 637-645)
  - Creates async tasks for agents with satisfied dependencies
  - Tracks concurrent execution count for metrics
  - Manages the active task pool

  3. Cleanup Phase (lines 648-691)

  After the main loop, it:
  - Waits for all remaining active tasks to complete
  - Processes final task results
  - Updates state with completion status
  - Ensures no agents are left unprocessed

  Key Design Features

  Dependency Resolution

  - Agents wait until their dependencies complete successfully
  - Failed dependencies prevent dependent agents from running
  - Prevents dependency deadlocks with retry limits

  Concurrency Control

  - Respects priority-based concurrency limits via semaphores
  - Tracks active tasks per priority level
  - Balances load across priority queues

  State Propagation

  - Each completed agent updates the shared state
  - State changes enable dependent agents to proceed
  - Maintains consistency across parallel executions

  Deadlock Prevention

  - Detects when only unsatisfiable dependencies remain
  - Limits dependency retry attempts
  - Logs and breaks out of potential deadlock situations

  Example Flow

  1. Agent A (no deps) → Starts immediately
  2. Agent B (depends on A) → Queued, waiting
  3. Agent C (no deps) → Starts in parallel with A
  4. A completes → State updated with A's results
  5. B's dependencies now satisfied → B starts
  6. All agents complete → Final state returned

  This method is the heart of the parallel execution system, orchestrating complex agent workflows while
  maintaining proper execution order based on dependencies and managing system resources efficiently.