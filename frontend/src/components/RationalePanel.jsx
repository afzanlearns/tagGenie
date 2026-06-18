export default function RationalePanel({ tag, rationale }) {
  if (!rationale) return null

  return (
    <div className="mt-1 mb-3 pl-8 text-xs" style={{ color: '#555' }}>
      <span className="font-medium" style={{ color: '#666' }}>{tag}</span>
      <span className="mx-2">—</span>
      {rationale}
    </div>
  )
}
