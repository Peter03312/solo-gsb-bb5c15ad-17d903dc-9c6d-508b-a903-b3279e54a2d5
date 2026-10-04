// Side-by-side comparison shown when two editors change the same event.
// The user picks which side to keep as the base, then lands back in the
// editor and can Save (revision attached) to retry.
export default function ConflictDialog({ conflict, onChoose, onCancel }) {
  const server = conflict.server_event;
  const submitted = conflict.submitted;

  const Row = ({ label, a, b }) => (
    <tr>
      <th>{label}</th>
      <td className={a === b ? "" : "diff"}>{a || <em>（空）</em>}</td>
      <td className={a === b ? "" : "diff"}>{b || <em>（空）</em>}</td>
    </tr>
  );

  return (
    <div className="modal-backdrop">
      <div className="modal modal-wide">
        <h2>⚠️ 并发修改冲突</h2>
        <p className="muted">
          您基于修订 <code>#{conflict.client_revision}</code> 编辑，但该事件已被他人保存为修订{" "}
          <code>#{conflict.server_revision}</code>。请对照两侧内容，选择一个版本继续编辑后再保存。
        </p>
        <div className="conflict-cols">
          <table className="diff-table">
            <thead>
              <tr>
                <th></th>
                <th>服务器最新版本 #{conflict.server_revision}</th>
                <th>您尚未保存的改动</th>
              </tr>
            </thead>
            <tbody>
              <Row label="标题" a={server.title} b={submitted.title} />
              <Row label="日期" a={server.event_date} b={submitted.event_date} />
              <Row label="地点" a={server.location} b={submitted.location} />
              <Row label="说明" a={server.description} b={submitted.description} />
              <tr>
                <th>引文</th>
                <td className={server.quotes.length === submitted.quotes.length ? "" : "diff"}>
                  {server.quotes.length} 条
                  <ul className="mini-quotes">
                    {server.quotes.map((q, i) => (
                      <li key={i}>
                        {q.start_sec}–{q.end_sec}s：{q.text}
                      </li>
                    ))}
                  </ul>
                </td>
                <td className={server.quotes.length === submitted.quotes.length ? "" : "diff"}>
                  {submitted.quotes.length} 条
                  <ul className="mini-quotes">
                    {submitted.quotes.map((q, i) => (
                      <li key={i}>
                        {q.start_sec}–{q.end_sec}s：{q.text}
                      </li>
                    ))}
                  </ul>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="modal-actions">
          <button className="btn" onClick={onCancel}>
            取消
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onChoose({ base: "mine", server })}
          >
            保留我的改动为基础
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onChoose({ base: "server", server })}
          >
            采用服务器最新版
          </button>
        </div>
        <p className="hint">
          无论选择哪个，保存时都会以最新修订号 <code>#{conflict.server_revision + 1}</code>{" "}
          提交；您也可以在编辑器里把两侧内容手工合并后再保存。
        </p>
      </div>
    </div>
  );
}
