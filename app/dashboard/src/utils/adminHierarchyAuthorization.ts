type CurrentAdmin = {
  id?: number | null;
  role?: string | null;
};

type ManagedHierarchyNode = {
  id: number;
  parent_admin_id: number | null;
};

export const canManageHierarchyNode = (
  current: CurrentAdmin,
  node: ManagedHierarchyNode
): boolean =>
  current.id !== node.id &&
  (current.role === "OWNER" || node.parent_admin_id === current.id);
