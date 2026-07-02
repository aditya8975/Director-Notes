const KIND_LABEL = {
  character: "char",
  scene: "scene",
  camera_angle: "angle",
  custom: "tag",
};

export default function TagPill({ tag, size = "sm", onRemove }) {
  return (
    <span
      className={`tag-pill tag-pill-${size}`}
      style={{
        "--pill-color": `var(--tag-${tag.kind})`,
        "--pill-color-dim": `var(--tag-${tag.kind}-dim)`,
      }}
      title={`${KIND_LABEL[tag.kind] || tag.kind}: ${tag.value}`}
    >
      <span className="tag-pill-dot" />
      {tag.value}
      {onRemove && (
        <button
          className="tag-pill-remove"
          onClick={(e) => {
            e.stopPropagation();
            onRemove(tag);
          }}
          aria-label={`Remove ${tag.value} tag`}
        >
          ×
        </button>
      )}
    </span>
  );
}
