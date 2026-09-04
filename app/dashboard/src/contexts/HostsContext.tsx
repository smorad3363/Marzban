import { fetch } from "service/http";
import { create } from "zustand";

export type HostsSchema = Record<
  string,
  {
    id?: number;
    remark: string;
    address: string;
    port: number | null;
    path: string | null;
    sni: string | null;
    host: string | null;
  }[]
>;

export type HostImpactAction = "apply_current" | "future_only" | "detach";

export type HostUpdateImpact = {
  affected_plan_count: number;
  affected_plan_version_count: number;
  active_user_count: number;
  affected_plan_ids: number[];
  affected_version_ids: number[];
  invalid_plan_ids: number[];
  changed_host_ids: number[];
  removed_host_ids: number[];
};

type HostsStore = {
  isLoading: boolean;
  isPostLoading: boolean;
  isImpactLoading: boolean;
  hosts: HostsSchema;
  fetchHosts: () => void;
  previewHosts: (hosts: HostsSchema) => Promise<HostUpdateImpact>;
  setHosts: (hosts: HostsSchema, action?: HostImpactAction) => Promise<void>;
};
export const useHosts = create<HostsStore>((set) => ({
  isLoading: false,
  isPostLoading: false,
  isImpactLoading: false,
  hosts: {},
  fetchHosts: () => {
    set({ isLoading: true });
    fetch("/hosts")
      .then((hosts) => set({ hosts }))
      .finally(() => set({ isLoading: false }));
  },
  previewHosts: (body) => {
    set({ isImpactLoading: true });
    return fetch<HostUpdateImpact>("/hosts/impact", { method: "POST", body }).finally(() => {
      set({ isImpactLoading: false });
    });
  },
  setHosts: (body, action) => {
    set({ isPostLoading: true });
    const query = action ? `?impact_action=${encodeURIComponent(action)}` : "";
    return fetch(`/hosts${query}`, { method: "PUT", body }).finally(() => {
      set({ isPostLoading: false });
    });
  },
}));
