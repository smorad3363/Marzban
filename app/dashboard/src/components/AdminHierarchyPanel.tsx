import {
  Alert, AlertIcon, Badge, Box, Button, Card, Checkbox, HStack, Input, Select,
  SimpleGrid, Skeleton, Stack, Text, useToast,
} from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { HierarchyAdminNode } from "types/Admin";
import { BulkJobResponse } from "types/User";
import { formatBytes } from "utils/formatByte";
import { localizedApiError } from "utils/apiError";
import { canManageHierarchyNode } from "utils/adminHierarchyAuthorization";

const GIB = 1024 ** 3;
const billingLabels: Record<string, string> = {
  USED_TRAFFIC: "مصرف واقعی", ALLOCATED_TRAFFIC: "حجم ساخته‌شده",
  USER_CREDIT: "حجم نامحدود · سقف اکانت", SEAT_CREDIT: "ظرفیت دستگاه قدیمی",
  LEGACY_COMPAT: "قدیمی (فقط مهاجرت)",
};
const roleLabels: Record<string, string> = { OWNER: "مالک", ADMIN: "ادمین" };
type FlatNode = HierarchyAdminNode & { visualDepth: number };
const flatten = (nodes: HierarchyAdminNode[], depth = 0): FlatNode[] => nodes.flatMap((node) => [{ ...node, visualDepth: depth }, ...flatten(node.children || [], depth + 1)]);
const resource = (mode: string) => mode === "USER_CREDIT" ? "user" : mode === "SEAT_CREDIT" ? "seat" : "traffic";
const unitLabel = (mode: string) => mode === "USER_CREDIT" ? "اکانت" : mode === "SEAT_CREDIT" ? "دستگاه" : "گیگابایت";
const toApiAmount = (mode: string, amount: number) => resource(mode) === "traffic" ? Math.round(amount * GIB) : Math.round(amount);
const creditText = (node: FlatNode) => node.available_traffic === null ? "نامحدود" : resource(node.billing_mode) === "traffic" ? String(formatBytes(node.available_traffic)) : `${node.available_traffic} ${unitLabel(node.billing_mode)}`;

export const AdminHierarchyPanel: FC = () => {
  const { userData } = useGetUser();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [amount, setAmount] = useState("");
  const [modeFilter, setModeFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const query = useQuery<HierarchyAdminNode[], Error>("admin-hierarchy-tree", () => fetch("/admin-management/tree"), { refetchInterval: 15000 });
  const allNodes = useMemo(() => flatten(query.data || []), [query.data]);
  const nodes = modeFilter ? allNodes.filter((node) => node.billing_mode === modeFilter) : allNodes;
  const selected = allNodes.filter((node) => selectedIds.includes(node.id));
  const selectedResource = selected[0] ? resource(selected[0].billing_mode) : null;
  const mixed = selected.some((node) => resource(node.billing_mode) !== selectedResource);

  const refresh = () => {
    queryClient.invalidateQueries("admin-hierarchy-tree");
    queryClient.invalidateQueries("admin-management");
    queryClient.invalidateQueries("account-summary");
  };

  const singleAction = useMutation(
    ({ node, operation }: { node: FlatNode; operation: "freeze" | "unfreeze" | "trial-reset" }) => {
      if (operation === "trial-reset") return fetch(`/admin-management/${node.username}/trial-quota/reset`, { method: "POST", body: { idempotency_key: `trial-reset-${node.id}-${crypto.randomUUID()}` } });
      return fetch(`/admin-management/${node.username}/${operation}`, {
        method: "POST",
        body: operation === "freeze"
          ? { reason_id: 1, idempotency_key: `freeze-${node.id}-${crypto.randomUUID()}` }
          : { idempotency_key: `unfreeze-${node.id}-${crypto.randomUUID()}` },
      });
    },
    { onSuccess: () => { refresh(); toast({ title: "عملیات انجام شد", status: "success" }); }, onError: (error) => { toast({ title: "عملیات انجام نشد", description: localizedApiError(error), status: "error" }); } }
  );

  const runBulk = async (operation: "grant_credit" | "reclaim_credit") => {
    const numeric = Number(amount);
    if (!selected.length || mixed || !Number.isFinite(numeric) || numeric <= 0) return;
    setBusy(true);
    try {
      const operationId = `bulk-admin-${crypto.randomUUID()}`;
      await fetch<BulkJobResponse>("/admin-management/bulk-credit/jobs", {
        method: "POST",
        body: { operation_id: operationId, operation, selected_admin_ids: selectedIds, amount: toApiAmount(selected[0].billing_mode, numeric) },
      });
      let result = await fetch<BulkJobResponse>(`/admin-management/bulk-credit/jobs/${operationId}/execute`, { method: "POST", body: { chunk_size: 100 } });
      while (result.has_more) result = await fetch<BulkJobResponse>(`/admin-management/bulk-credit/jobs/${operationId}/execute`, { method: "POST", body: { chunk_size: 100 } });
      refresh();
      setAmount("");
      toast({ title: `${result.success} انجام شد · ${result.failed + result.skipped} انجام نشد`, status: result.failed ? "warning" : "success" });
    } catch (error) {
      toast({ title: "عملیات گروهی انجام نشد", description: localizedApiError(error), status: "error" });
    } finally { setBusy(false); }
  };

  if (query.isLoading) return <Skeleton h="180px" borderRadius="14px" mb={4} />;
  if (query.isError) return <Alert status="error" mb={4}><AlertIcon />ساختار زیرمجموعه بارگذاری نشد.</Alert>;
  return (
    <Card mb={4} bg="var(--panel-surface)" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="14px" overflow="hidden">
      <HStack p={3} justify="space-between" align={{ base: "start", md: "center" }} flexWrap="wrap" borderBottomWidth="1px" borderColor="var(--panel-border)">
        <Box><Text fontWeight="800">زیرمجموعه‌ها</Text><Text mt={0.5} color="gray.400" fontSize="xs">انتخاب، اعتبار، فریز و ریست تست؛ بدون بازکردن فرم‌های بزرگ.</Text></Box>
        <Select aria-label="دسته‌بندی نوع اعتبار" value={modeFilter} maxW={{ base: "full", md: "230px" }} size="sm" onChange={(event) => { setModeFilter(event.target.value); setSelectedIds([]); }}>
          <option value="">همه نوع‌های اعتبار</option><option value="USED_TRAFFIC">مصرف واقعی</option><option value="ALLOCATED_TRAFFIC">حجم ساخته‌شده</option><option value="USER_CREDIT">نامحدود با سقف اکانت</option>
        </Select>
      </HStack>

      {selected.length > 0 && (
        <HStack position="sticky" top={0} zIndex={1} p={3} bg="var(--panel-nested)" borderBottomWidth="1px" borderColor="var(--panel-border)" flexWrap="wrap">
          <Badge colorScheme={mixed ? "red" : "yellow"}>{selected.length} انتخاب</Badge>
          {mixed ? <Text fontSize="xs" color="red.200">برای عملیات گروهی، نوع واحد اعتبار باید یکسان باشد.</Text> : <>
            <Input aria-label="مقدار عملیات گروهی" type="number" min={1} step={resource(selected[0].billing_mode) === "traffic" ? 0.1 : 1} value={amount} onChange={(event) => setAmount(event.target.value)} placeholder={`مقدار (${unitLabel(selected[0].billing_mode)})`} maxW="190px" size="sm" />
            <Button size="sm" colorScheme="primary" isLoading={busy} isDisabled={Number(amount) <= 0} onClick={() => runBulk("grant_credit")}>افزودن اعتبار</Button>
            <Button size="sm" variant="outline" isLoading={busy} isDisabled={Number(amount) <= 0} onClick={() => runBulk("reclaim_credit")}>پس‌گرفتن</Button>
          </>}
          <Button size="xs" ms="auto" variant="ghost" onClick={() => setSelectedIds([])}>پاک‌کردن انتخاب</Button>
        </HStack>
      )}

      <Stack p={3} spacing={2}>
        {nodes.map((node) => {
          const canAct = canManageHierarchyNode(userData, node) && node.role !== "OWNER";
          const frozen = node.active_owner_freeze_event_id !== null;
          return <Box key={node.id} p={3} ps={{ base: 3, md: `${12 + node.visualDepth * 18}px` }} bg="var(--panel-nested)" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px">
            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={2} alignItems="center">
              <HStack minW={0} flexWrap="wrap">
                {canAct && <Checkbox aria-label={`انتخاب ${node.username}`} isChecked={selectedIds.includes(node.id)} onChange={(event) => setSelectedIds((current) => event.target.checked ? [...new Set([...current, node.id])] : current.filter((id) => id !== node.id))} />}
                <Text dir="ltr" fontWeight="750">{node.username}</Text>
                <Badge>{roleLabels[node.role] || node.role}</Badge>
                <Badge variant="outline" colorScheme={node.billing_mode === "USER_CREDIT" ? "purple" : "yellow"}>{billingLabels[node.billing_mode] || node.billing_mode}</Badge>
                {frozen && <Badge colorScheme="orange">فریز</Badge>}
              </HStack>
              <HStack justify={{ lg: "end" }} flexWrap="wrap" spacing={2}>
                <Text color="gray.400" fontSize="xs">اعتبار: {creditText(node)} · تست قابل ساخت: {node.trial_quota}</Text>
                {canAct && <Button size="xs" variant="ghost" colorScheme="orange" isLoading={singleAction.isLoading} onClick={() => window.confirm(frozen ? `فریز ${node.username} باز شود؟` : `${node.username} و زیرشاخه‌اش فریز شوند؟`) && singleAction.mutate({ node, operation: frozen ? "unfreeze" : "freeze" })}>{frozen ? "رفع فریز" : "فریز"}</Button>}
                {canAct && <Button size="xs" variant="ghost" isLoading={singleAction.isLoading} onClick={() => window.confirm(`تعداد تست قابل ساخت ${node.username} به سقفش برگردد؟`) && singleAction.mutate({ node, operation: "trial-reset" })}>ریست تست</Button>}
              </HStack>
            </SimpleGrid>
          </Box>;
        })}
        {nodes.length === 0 && <Text py={6} textAlign="center" color="gray.400">زیرمجموعه‌ای در این دسته نیست.</Text>}
      </Stack>
    </Card>
  );
};
