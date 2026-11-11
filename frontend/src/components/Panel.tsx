import type { HTMLAttributes, ReactNode } from "react";

interface PanelProps extends Omit<HTMLAttributes<HTMLElement>, "title"> {
  title?: ReactNode;
  actions?: ReactNode;
  as?: "section" | "aside" | "nav" | "div";
}

export function Panel({ title, actions, as: Tag = "section", className = "", children, ...rest }: PanelProps) {
  return (
    <Tag className={`panel map-zone ${className}`} {...rest}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-2 px-4 pt-3">
          {title && <h2 className="panel-title">{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
