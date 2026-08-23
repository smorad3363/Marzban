export type PlanInboundOption = {
  tag: string;
  protocol: string;
  network: string;
  tls: string;
  port?: number;
};

export const normalizePlanInboundTags = (tags: readonly string[]): string[] =>
  [...new Set(tags.map((tag) => tag.trim()).filter(Boolean))].sort();

export const collectPlanInboundOptions = (
  inbounds: ReadonlyMap<string, readonly PlanInboundOption[]>
): PlanInboundOption[] => {
  const byTag = new Map<string, PlanInboundOption>();
  for (const group of inbounds.values()) {
    for (const inbound of group) {
      if (!byTag.has(inbound.tag)) byTag.set(inbound.tag, inbound);
    }
  }
  return [...byTag.values()].sort((left, right) =>
    left.tag.localeCompare(right.tag)
  );
};

export const togglePlanInboundTag = (
  selected: readonly string[],
  tag: string,
  checked: boolean
): string[] =>
  normalizePlanInboundTags(
    checked ? [...selected, tag] : selected.filter((value) => value !== tag)
  );

export const missingPlanInboundTags = (
  selected: readonly string[],
  options: readonly PlanInboundOption[]
): string[] => {
  const configured = new Set(options.map((option) => option.tag));
  return normalizePlanInboundTags(selected).filter((tag) => !configured.has(tag));
};

export const normalizePlanHostScope = (
  hosts: Readonly<Record<string, readonly number[]>>
): Record<string, number[]> =>
  Object.fromEntries(
    Object.entries(hosts)
      .map(([tag, ids]) => [
        tag.trim(),
        [...new Set(ids.filter((id) => Number.isInteger(id) && id > 0))].sort((a, b) => a - b),
      ] as const)
      .filter(([tag]) => Boolean(tag))
      .sort(([left], [right]) => left.localeCompare(right))
  );

export const togglePlanHostId = (
  hosts: Readonly<Record<string, readonly number[]>>,
  inboundTag: string,
  hostId: number,
  checked: boolean
): Record<string, number[]> =>
  normalizePlanHostScope({
    ...hosts,
    [inboundTag]: checked
      ? [...(hosts[inboundTag] || []), hostId]
      : (hosts[inboundTag] || []).filter((id) => id !== hostId),
  });

export const missingPlanHostIds = (
  hosts: Readonly<Record<string, readonly number[]>>,
  options: readonly { tag: string; hosts: readonly { id: number }[] }[]
): number[] => {
  const available = new Map(options.map((option) => [
    option.tag,
    new Set(option.hosts.map((host) => host.id)),
  ]));
  return [...new Set(
    Object.entries(hosts).flatMap(([tag, ids]) =>
      ids.filter((id) => !available.get(tag)?.has(id))
    )
  )].sort((a, b) => a - b);
};
