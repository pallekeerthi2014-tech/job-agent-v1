import { MatchTable } from "../components/MatchTable";
import type { Candidate, Job, Match } from "../types";

type CandidateListPageProps = {
  matches: Match[];
  candidateMap: Map<number, Candidate>;
  jobMap: Map<number, Job>;
  onSelectMatch: (match: Match) => void;
};

export function CandidateListPage({ matches, candidateMap, jobMap, onSelectMatch }: CandidateListPageProps) {
  return <MatchTable matches={matches} candidateMap={candidateMap} jobMap={jobMap} onSelectMatch={onSelectMatch} />;
}

