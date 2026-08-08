import type { ContactCategory } from "../api/types";

const LABELS: Record<ContactCategory, string> = {
  CERTIFICATION_MANAGER: "Certification",
  PRODUCT_COMPLIANCE: "Compliance",
  REGULATORY_AFFAIRS: "Regulatory",
  PRODUCT_SECURITY: "Security",
  QUALITY: "Quality",
  ENGINEERING: "Engineering",
  EXECUTIVE: "Executive",
  IGNORE: "Other",
};

export function CategoryBadge({ category }: { category: ContactCategory }) {
  const cls = `badge badge--${category.toLowerCase()}`;
  return <span className={cls}>{LABELS[category] ?? category}</span>;
}
