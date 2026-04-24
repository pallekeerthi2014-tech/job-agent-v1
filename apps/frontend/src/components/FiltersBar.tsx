import type { Candidate, Employee, PriorityFilter } from "../types";

type FiltersBarProps = {
  candidates: Candidate[];
  employees: Employee[];
  canFilterByEmployee: boolean;
  selectedCandidateId: number | null;
  selectedEmployeeId: number | null;
  selectedPriority: PriorityFilter;
  onCandidateChange: (value: number | null) => void;
  onEmployeeChange: (value: number | null) => void;
  onPriorityChange: (value: PriorityFilter) => void;
};

export function FiltersBar({
  candidates,
  employees,
  canFilterByEmployee,
  selectedCandidateId,
  selectedEmployeeId,
  selectedPriority,
  onCandidateChange,
  onEmployeeChange,
  onPriorityChange
}: FiltersBarProps) {
  return (
    <section className="panel filters-bar">
      <div className="filter-field">
        <label htmlFor="candidateFilter">Candidate</label>
        <select
          id="candidateFilter"
          value={selectedCandidateId ?? ""}
          onChange={(event) => onCandidateChange(event.target.value ? Number(event.target.value) : null)}
        >
          <option value="">All candidates</option>
          {candidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.name}
            </option>
          ))}
        </select>
      </div>

      {canFilterByEmployee ? (
        <div className="filter-field">
          <label htmlFor="employeeFilter">Employee</label>
          <select
            id="employeeFilter"
            value={selectedEmployeeId ?? ""}
            onChange={(event) => onEmployeeChange(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">All employees</option>
            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.name}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <div className="filter-field">
        <label htmlFor="priorityFilter">Priority</label>
        <select
          id="priorityFilter"
          value={selectedPriority}
          onChange={(event) => onPriorityChange(event.target.value as PriorityFilter)}
        >
          <option value="All">All priorities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
      </div>
    </section>
  );
}
