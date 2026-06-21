import React from 'react';

interface Props {
  useUrl: boolean;
  setUseUrl: (v: boolean) => void;
  prUrl: string;
  setPrUrl: (v: string) => void;
  owner: string;
  setOwner: (v: string) => void;
  repo: string;
  setRepo: (v: string) => void;
  prNumber: string;
  setPrNumber: (v: string) => void;
  /** unique prefix so id attributes don't collide when both PR & Drift forms mount */
  idPrefix?: string;
}

/**
 * Shared PR reference input — used by PR Intelligence and Architecture Drift.
 * Owns: URL vs (owner/repo/number) toggle + labelled inputs.
 */
export const PRReferenceForm: React.FC<Props> = ({
  useUrl, setUseUrl,
  prUrl, setPrUrl,
  owner, setOwner,
  repo, setRepo,
  prNumber, setPrNumber,
  idPrefix = 'pr',
}) => (
  <div className="flex flex-col gap-4">
    <div role="tablist" aria-label="Reference type" className="flex gap-4 border-b border-border pb-3">
      {(['url', 'coords'] as const).map((k) => {
        const active = (k === 'url') === useUrl;
        return (
          <button
            key={k}
            role="tab"
            type="button"
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => setUseUrl(k === 'url')}
            className={[
              'text-sm font-semibold pb-2 border-b-2 transition-colors',
              'focus-visible:outline-none focus-visible:shadow-ring',
              active
                ? 'text-primary border-primary'
                : 'text-text-muted border-transparent hover:text-text',
            ].join(' ')}
          >
            {k === 'url' ? 'PR URL' : 'Repository Coordinates'}
          </button>
        );
      })}
    </div>

    {useUrl ? (
      <Field id={`${idPrefix}-url`} label="GitHub Pull Request URL">
        <input
          id={`${idPrefix}-url`}
          type="text"
          className="input"
          placeholder="https://github.com/owner/repo/pull/123"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
        />
      </Field>
    ) : (
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Field id={`${idPrefix}-owner`} label="Owner">
          <input
            id={`${idPrefix}-owner`}
            type="text"
            className="input"
            placeholder="VarshithReddy2006"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
          />
        </Field>
        <Field id={`${idPrefix}-repo`} label="Repository">
          <input
            id={`${idPrefix}-repo`}
            type="text"
            className="input"
            placeholder="Repo-Intelligence-Agent"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
          />
        </Field>
        <Field id={`${idPrefix}-number`} label="PR #">
          <input
            id={`${idPrefix}-number`}
            type="text"
            inputMode="numeric"
            className="input"
            placeholder="1"
            value={prNumber}
            onChange={(e) => setPrNumber(e.target.value)}
          />
        </Field>
      </div>
    )}
  </div>
);

const Field: React.FC<{ id: string; label: string; children: React.ReactNode }> = ({
  id, label, children,
}) => (
  <div className="flex flex-col gap-1.5">
    <label htmlFor={id} className="text-xs font-semibold text-text-muted">
      {label}
    </label>
    {children}
  </div>
);

export default PRReferenceForm;
