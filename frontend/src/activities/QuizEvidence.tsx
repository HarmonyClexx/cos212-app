import type { QuizEvidence, QuizEvidenceSummary, QuizItem, ResponseKind } from '../api/types'
import { ItemView } from './items/QuizItems'

const KIND_LABELS: Record<ResponseKind, string> = {
  first_unassisted_practice: 'First answer · no recorded help (practice)',
  first_assisted_practice: 'First answer · helped practice',
  repeat_practice: 'First answer · repeat practice',
  history_unknown: 'First recorded answer · earlier history not recorded',
  assisted_retry: 'Helped retry',
  repeat_response: 'Repeat response',
  final_fixed_set: 'Final response · fixed question set, not reserved independent evidence',
  final_reserved_unassisted: 'Reserved final response · no recorded help before submission',
  final_reserved_assisted: 'Reserved final response · recorded help before submission',
  final_repeat: 'Repeat practice · previously issued final version',
}
const HELP_LABELS: Record<string, string> = {
  hint: 'Requested hint',
  corrective_feedback: 'Corrective feedback after a checked answer',
  worked_explanation: 'Worked explanation after a correct answer',
  reveal: 'Revealed answer',
  review_topic: 'Requested topic review',
  study_activity: 'Requested lesson/practice navigation for this attempt',
  final_feedback: 'Feedback after whole-trial submission',
}

export function ItemResponseEvidence({ item, evidence }: { item: QuizItem; evidence?: QuizEvidence }) {
  const row = evidence?.items.find((r) => r.item_id === item.id)
  const first = row?.first_response
  const latest = row?.latest_response
  return (
    <details className="response-evidence small" style={{ marginTop: 14 }} aria-label={`Recorded responses for ${item.id}`}>
      <summary style={{ cursor: 'pointer' }}>
        <b>{first ? `${first.correct ? 'Correct' : 'Not fully correct'} first recorded answer`
          : row?.unanswered ? 'Unanswered at submission · no response recorded'
            : evidence?.schema_version ? 'No submitted answer recorded' : 'Earlier response history not recorded'}</b>
      </summary>
      <div className="stack-v" style={{ marginTop: 10 }}>
        {!evidence?.complete_from_start && <p className="muted">
          Earlier first-answer or assistance history was not recorded. New records do not reconstruct that gap.
        </p>}
        {first && (
          <>
            <p><b>{KIND_LABELS[first.kind]}</b></p>
            <p className="faint">Task v{first.bank_version} · {first.task_version.slice(0, 12)}</p>
            <p><b>Original submitted answer</b></p>
            <ItemView item={item} value={first.answer} locked onChange={() => {}}
              reflection={first.reflection ?? undefined} />
            {first.assistance_before.length > 0 && <p className="muted">Help was recorded before this response.</p>}
            {first.independent_final && <p className="muted">
              An unassisted response on a reserved version unused at issuance, not proof of general mastery or absence of outside help.
            </p>}
            {latest && latest.sequence !== first.sequence && <p>
              Latest recorded answer: <b>{latest.correct ? 'correct' : 'not fully correct'}</b> · {KIND_LABELS[latest.kind]}.
              The original answer above is unchanged.
            </p>}
          </>
        )}
        {(row?.assistance.length ?? 0) > 0 && (
          <div>
            <p><b>Recorded support</b> · requests/disclosures, not proof the content was read</p>
            <ul style={{ paddingLeft: 20 }}>
              {row!.assistance.map((a, i) => (
                <li key={`${a.revision}-${a.sequence ?? i}`}>
                  {HELP_LABELS[a.action] ?? a.action}{a.level ? ` · level ${a.level}` : ''}{a.source === 'L1' ? ' · earlier review record' : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="faint">Draft edits are not submitted answers. No recorded help does not prove no other help was used.</p>
      </div>
    </details>
  )
}

const COLUMNS: [ResponseKind, string][] = [
  ['first_unassisted_practice', 'First · no recorded help'],
  ['first_assisted_practice', 'Helped first'],
  ['repeat_practice', 'Repeat first'],
  ['assisted_retry', 'Helped retries'],
  ['repeat_response', 'Other repeats'],
  ['history_unknown', 'Partial history'],
  ['final_fixed_set', 'Fixed-set final'],
  ['final_reserved_unassisted', 'Reserved final · no recorded help'],
  ['final_reserved_assisted', 'Reserved final · helped'],
  ['final_repeat', 'Final repeat practice'],
]

export function RecordedQuizSummary({ summary }: { summary?: QuizEvidenceSummary }) {
  if (!summary) return (
    <section className="card small" aria-label="Recorded quiz responses">
      First-response tracking is not available for this earlier response.
    </section>
  )
  return (
    <section className="card" aria-label="Recorded quiz responses">
      <h2 style={{ fontSize: 18 }}>Recorded quiz responses</h2>
      <p className="small muted" style={{ margin: '10px 0' }}>
        Fully correct / recorded responses, separate from running scores and reward credit.
        First formative answers are practice, not independent assessments. Reserved-final records separate
        responses without recorded help from helped responses. Fixed-set and repeated finals are not fresh independent checks.
      </p>
      <div style={{ overflowX: 'auto' }} tabIndex={0} role="region" aria-label="Recorded response counts">
        <table className="table">
          <thead><tr><th>Objective</th>{COLUMNS.map(([kind, label]) => <th key={kind}>{label}</th>)}</tr></thead>
          <tbody>{summary.objectives.map((row) => (
            <tr key={row.objective}>
              <td><b>{row.objective}</b></td>
              {COLUMNS.map(([kind]) => (
                <td key={kind}>{row[kind]?.total ? `${row[kind].correct} / ${row[kind].total}` : '—'}</td>
              ))}
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="small faint" style={{ marginTop: 10 }}>
        A dash means no recorded responses, not an assessed zero. Lessons, guided traces and demonstrations remain practice.
        No recorded help does not establish that no other help was used.
      </p>
      {summary.unrecorded_attempts > 0 && <p className="small muted" style={{ marginTop: 8 }}>
        {summary.unrecorded_attempts} quiz attempt(s) have missing or partial earlier history; it has not been backfilled.
      </p>}
      {summary.unanswered_final_items > 0 && <p className="small muted" style={{ marginTop: 8 }}>
        {summary.unanswered_final_items} final item(s) were unanswered: they retain the existing zero-score policy but are not recorded submitted mistakes.
      </p>}
    </section>
  )
}

export function FinalAssignmentStatus({ evidence }: { evidence?: QuizEvidence }) {
  const assigned = evidence?.final_assignment
  return <p className="small muted" style={{ marginTop: 12 }} role="status">
    {!assigned ? 'Legacy fixed question set - not reserved independent evidence.'
      : assigned.purpose === 'repeat'
        ? `Repeat practice - final version ${assigned.variant}. This version was already issued; it supplies no new independent final evidence.`
        : `Reserved final ${assigned.variant} - unused at issuance. Refreshing or returning continues this same assigned version, not a new final.`}
  </p>
}
