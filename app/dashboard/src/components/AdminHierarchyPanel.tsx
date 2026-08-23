import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  useToast,
} from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { HierarchyAdminNode } from "types/Admin";
import { BulkJobResponse, BulkPreviewResponse } from "types/User";
import { formatBytes } from "utils/formatByte";
import { localizedApiError } from "utils/apiError";
import { canManageHierarchyNode } from "utils/adminHierarchyAuthorization";

const GIB = 1024 ** 3;

type FlatNode = HierarchyAdminNode & { visualDepth: number };

const flatten = (nodes: HierarchyAdminNode[], visualDepth = 0): FlatNode[] =>
  nodes.flatMap((node) => [
    { ...node, visualDepth },
    ...flatten(node.children || [], visualDepth + 1),
  ]);

const errorText = localizedApiError;

export const AdminHierarchyPanel: FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { userData } = useGetUser();
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [reasons, setReasons] = useState<Record<number, string>>({});
  const [trialAmounts, setTrialAmounts] = useState<Record<number, string>>({});
  const [trialReasons, setTrialReasons] = useState<Record<number, string>>({});
  const [renewalEnabled, setRenewalEnabled] = useState<Record<number, boolean>>({});
  const [renewalRemaining, setRenewalRemaining] = useState<Record<number, string>>({});
  const [referrers, setReferrers] = useState<Record<number, string>>({});
  const [referralRates, setReferralRates] = useState<Record<number, string>>({});
  const [referralNotes, setReferralNotes] = useState<Record<number, string>>({});
  const [bulkAdminIds, setBulkAdminIds] = useState<number[]>([]);
  const [bulkAmount, setBulkAmount] = useState("");
  const [bulkReason, setBulkReason] = useState("");
  const [bulkPreview, setBulkPreview] = useState<BulkPreviewResponse | null>(null);
  const [bulkResult, setBulkResult] = useState<BulkJobResponse | null>(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const query = useQuery<HierarchyAdminNode[], Error>(
    "admin-hierarchy-tree",
    () => fetch("/admin-management/tree"),
    { refetchInterval: 15000 }
  );
  const nodes = useMemo(() => flatten(query.data || []), [query.data]);

  useEffect(() => {
    if (bulkAdminIds.length === 0) {
      setBulkPreview(null);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const preview = await fetch<BulkPreviewResponse>(
          "/admin-management/bulk-credit/preview",
          {
            method: "POST",
            body: { selected_admin_ids: bulkAdminIds },
            signal: controller.signal,
          }
        );
        setBulkPreview(preview);
      } catch (error) {
        if (!controller.signal.aborted) {
          setBulkPreview(null);
          toast({ title: "پیش‌نمایش ادمین‌ها ناموفق بود", description: errorText(error), status: "error" });
        }
      }
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [bulkAdminIds, toast]);

  const runBulkCredit = async (
    operation: "grant_credit" | "reclaim_credit",
    retryOperationId?: string
  ) => {
    const amount = Number(bulkAmount);
    if (!retryOperationId && (!bulkPreview || !Number.isFinite(amount) || amount <= 0 || !bulkReason.trim())) return;
    setBulkBusy(true);
    try {
      const operationId = retryOperationId || `bulk-admin-${crypto.randomUUID()}`;
      if (!retryOperationId) {
        await fetch<BulkJobResponse>("/admin-management/bulk-credit/jobs", {
          method: "POST",
          body: {
            operation_id: operationId,
            operation,
            selected_admin_ids: bulkAdminIds,
            amount: Math.round(amount * GIB),
            note: bulkReason.trim(),
          },
        });
      }
      let current = await fetch<BulkJobResponse>(
        `/admin-management/bulk-credit/jobs/${operationId}/execute`,
        {
          method: "POST",
          body: { chunk_size: 100, retry_failed: Boolean(retryOperationId) },
        }
      );
      while (current.has_more) {
        current = await fetch<BulkJobResponse>(
          `/admin-management/bulk-credit/jobs/${operationId}/execute`,
          {
            method: "POST",
            body: { chunk_size: 100, retry_failed: Boolean(retryOperationId) },
          }
        );
      }
      setBulkResult(current);
      queryClient.invalidateQueries("admin-hierarchy-tree");
      queryClient.invalidateQueries("account-summary");
      toast({
        title: `موفق ${current.success} · ناموفق ${current.failed} · نادیده‌گرفته ${current.skipped}`,
        status: current.failed ? "warning" : "success",
      });
    } catch (error) {
      toast({ title: "عملیات گروهی اعتبار انجام نشد", description: errorText(error), status: "error" });
    } finally {
      setBulkBusy(false);
    }
  };

  const action = useMutation(
    ({ node, operation, amount, reason, enabled, remaining, referrer, rateBps }: {
      node: FlatNode;
      operation: "grant" | "reclaim" | "trial-grant" | "trial-reclaim" | "renewal" | "suspend" | "resume" | "freeze" | "unfreeze" | "referral-set" | "referral-remove";
      amount?: number;
      reason?: string;
      enabled?: boolean;
      remaining?: number | null;
      referrer?: string;
      rateBps?: number;
    }) => {
      if (operation === "grant" || operation === "reclaim") {
        return fetch(`/admin-management/${node.username}/credit/${operation}`, {
          method: "POST",
          body: {
            amount,
            idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}`,
            note: reason,
          },
        });
      }
      if (operation === "trial-grant" || operation === "trial-reclaim") {
        const adjustment = operation === "trial-grant" ? "grant" : "reclaim";
        return fetch(`/admin-management/${node.username}/trial-quota/${adjustment}`, {
          method: "POST",
          body: {
            amount,
            idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}`,
            note: reason,
          },
        });
      }
      if (operation === "renewal") {
        return fetch(`/admin-management/${node.username}/renewal-policy`, {
          method: "PUT",
          body: { enabled, remaining },
        });
      }
      if (operation === "referral-set" || operation === "referral-remove") {
        return fetch(`/admin-management/${node.username}/referral`, {
          method: operation === "referral-set" ? "PUT" : "DELETE",
          body: operation === "referral-set"
            ? { referrer_username: referrer, rate_bps: rateBps, note: reason, idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}` }
            : { note: reason, idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}` },
        });
      }
      return fetch(`/admin-management/${node.username}/${operation}`, {
        method: "POST",
        body: operation === "freeze"
          ? { reason_id: 1, note: reason, idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}` }
          : operation === "unfreeze"
            ? { idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}` }
            : operation === "suspend"
              ? { reason_id: 1, include_subtree: true }
              : undefined,
      });
    },
    {
      onSuccess: (_data, variables) => {
        queryClient.invalidateQueries("admin-hierarchy-tree");
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("account-summary");
        if (variables.operation === "grant" || variables.operation === "reclaim") {
          setAmounts((current) => ({ ...current, [variables.node.id]: "" }));
          setReasons((current) => ({ ...current, [variables.node.id]: "" }));
        }
        if (variables.operation === "trial-grant" || variables.operation === "trial-reclaim") {
          setTrialAmounts((current) => ({ ...current, [variables.node.id]: "" }));
          setTrialReasons((current) => ({ ...current, [variables.node.id]: "" }));
        }
        toast({ title: "عملیات با موفقیت انجام شد", status: "success", duration: 3000 });
      },
      onError: (error) => { toast({ title: "عملیات انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
    }
  );

  if (query.isLoading) return <Skeleton h="190px" borderRadius="18px" mb={5} />;
  if (query.isError) return <Alert status="error" mb={5}><AlertIcon />درخت مدیریتی دریافت نشد.</Alert>;

  return (
    <Card mb={5} p={{ base: 4, md: 5 }} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="18px" boxShadow="panel">
      <Box mb={4}>
        <Text as="h2" fontSize="lg" fontWeight="800">ساختار سلسله‌مراتبی</Text>
        <Text color="gray.400" fontSize="sm" mt={1}>نقش، وضعیت حساب و اعتبار قابل‌انتقال هر شاخه.</Text>
      </Box>
      <Stack mb={4} p={4} spacing={3} bg="blackAlpha.300" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="12px">
        <Text fontWeight="800">Grant / Reclaim گروهی</Text>
        <Text fontSize="sm" color="gray.300">
          ادمین‌ها را از checkbox هر ردیف انتخاب کنید. پیش‌نمایش سرور قبل از اجرا الزامی است.
        </Text>
        <HStack align="end" spacing={2} flexWrap="wrap">
          <FormControl maxW={{ md: "170px" }} isRequired>
            <FormLabel fontSize="xs">اعتبار برای هر ادمین (GiB)</FormLabel>
            <Input minH="44px" type="number" min={0.01} step={0.01} dir="ltr" value={bulkAmount} onChange={(event) => setBulkAmount(event.target.value)} />
          </FormControl>
          <FormControl flex="1" minW={{ base: "100%", md: "240px" }} isRequired>
            <FormLabel fontSize="xs">دلیل</FormLabel>
            <Input minH="44px" maxLength={512} value={bulkReason} onChange={(event) => setBulkReason(event.target.value)} />
          </FormControl>
          <Button minH="44px" colorScheme="green" isLoading={bulkBusy} isDisabled={!bulkPreview || !bulkReason.trim() || Number(bulkAmount) <= 0} onClick={() => runBulkCredit("grant_credit")}>Grant</Button>
          <Button minH="44px" variant="outline" isLoading={bulkBusy} isDisabled={!bulkPreview || !bulkReason.trim() || Number(bulkAmount) <= 0} onClick={() => runBulkCredit("reclaim_credit")}>Reclaim</Button>
        </HStack>
        <Alert status={bulkPreview ? "info" : "warning"} borderRadius="10px">
          <AlertIcon />
          {bulkPreview
            ? `${bulkPreview.resolved_target_count} ادمین snapshot می‌شود.`
            : "حداقل یک ادمین مجاز انتخاب کنید."}
        </Alert>
        {bulkResult && (
          <Box fontSize="sm" aria-live="polite">
            <Text fontWeight="700">job {bulkResult.status}: کل {bulkResult.total} · موفق {bulkResult.success} · ناموفق {bulkResult.failed} · نادیده‌گرفته {bulkResult.skipped}</Text>
            {bulkResult.failed > 0 && (
              <Button mt={2} minH="44px" size="sm" variant="outline" isLoading={bulkBusy} onClick={() => runBulkCredit(bulkResult.operation as "grant_credit" | "reclaim_credit", bulkResult.operation_id)}>
                Retry خطاهای قابل‌تکرار
              </Button>
            )}
          </Box>
        )}
      </Stack>
      <Stack spacing={2}>
        {nodes.map((node) => {
          const canAct = canManageHierarchyNode(userData, node);
          const amount = Number(amounts[node.id] || 0);
          const reason = reasons[node.id] || "";
          const trialAmount = Number(trialAmounts[node.id] || 0);
          const trialReason = trialReasons[node.id] || "";
          const enabled = renewalEnabled[node.id] ?? node.renewal_enabled;
          const remainingText = renewalRemaining[node.id] ?? (node.renewal_remaining === null ? "" : String(node.renewal_remaining));
          const remaining = remainingText === "" ? null : Number(remainingText);
          const isOwner = userData.role === "OWNER" || userData.is_sudo;
          const currentReferrer = nodes.find((candidate) => candidate.id === node.referral_referrer_admin_id)?.username || "";
          const referrer = referrers[node.id] ?? currentReferrer;
          const referralRateText = referralRates[node.id] ?? (node.referral_rate_bps === null ? "" : String(node.referral_rate_bps));
          const referralRate = Number(referralRateText);
          const referralNote = referralNotes[node.id] || "";
          return (
            <Box key={node.id} p={3} ps={{ base: 3, md: `${12 + node.visualDepth * 24}px` }} bg="rgba(255,255,255,.025)" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="12px">
              <SimpleGrid columns={{ base: 1, xl: 2 }} gap={3} alignItems="center">
                <Box minW={0}>
                  <HStack flexWrap="wrap">
                    {canAct && node.parent_admin_id !== null && (
                      <Checkbox
                        minW="44px"
                        minH="44px"
                        aria-label={`انتخاب ${node.username} برای عملیات گروهی اعتبار`}
                        isChecked={bulkAdminIds.includes(node.id)}
                        onChange={(event) =>
                          setBulkAdminIds((current) =>
                            event.target.checked
                              ? [...current, node.id].sort((a, b) => a - b)
                              : current.filter((id) => id !== node.id)
                          )
                        }
                      />
                    )}
                    <Text fontWeight="750" dir="ltr" overflowWrap="anywhere">{node.username}</Text>
                    <Badge colorScheme={node.role === "OWNER" ? "purple" : node.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{node.role.replace("_", " ")}</Badge>
                    <Badge colorScheme={node.account_status === "ACTIVE" ? "green" : "orange"}>{node.account_status}</Badge>
                  </HStack>
                  <Text mt={1} color="gray.400" fontSize="xs">عمق {node.visualDepth} · اعتبار: {node.available_traffic === null ? "نامحدود" : String(formatBytes(node.available_traffic))} · Trial باقی‌مانده: {node.trial_quota}</Text>
                </Box>
                <HStack spacing={3} fontSize="xs" color="gray.300" flexWrap="wrap">
                  <Text>مصرف: {formatBytes(node.own_spend)}</Text>
                  <Text>واگذارشده: {formatBytes(node.delegated_traffic)}</Text>
                  <Text>API: {node.external_api_enabled ? "فعال" : "خاموش"}</Text>
                </HStack>
              </SimpleGrid>
              {canAct && (
                <SimpleGrid columns={{ base: 1, xl: 2 }} gap={3} mt={3}>
                  <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2} p={3} bg="blackAlpha.200" borderRadius="10px">
                    <FormControl maxW={{ md: "145px" }}>
                      <FormLabel fontSize="xs" mb={1}>اعتبار (GiB)</FormLabel>
                      <Input minH="44px" type="number" min={0.01} step={0.01} dir="ltr" value={amounts[node.id] || ""} onChange={(event) => setAmounts((current) => ({ ...current, [node.id]: event.target.value }))} />
                    </FormControl>
                    <FormControl flex="1">
                      <FormLabel fontSize="xs" mb={1}>دلیل تغییر</FormLabel>
                      <Input minH="44px" maxLength={512} value={reason} onChange={(event) => setReasons((current) => ({ ...current, [node.id]: event.target.value }))} />
                    </FormControl>
                    <Button minH="44px" size="sm" colorScheme="green" isDisabled={!Number.isFinite(amount) || amount <= 0 || !reason.trim()} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "grant", amount: Math.round(amount * GIB), reason: reason.trim() })}>واگذاری</Button>
                    <Button minH="44px" size="sm" variant="outline" isDisabled={!Number.isFinite(amount) || amount <= 0 || !reason.trim()} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "reclaim", amount: Math.round(amount * GIB), reason: reason.trim() })}>بازپس‌گیری</Button>
                  </Stack>
                  <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2} p={3} bg="blackAlpha.200" borderRadius="10px">
                    <FormControl maxW={{ md: "150px" }}>
                      <FormLabel fontSize="xs" mb={1}>اجازه تمدید</FormLabel>
                      <Select minH="44px" value={enabled ? "enabled" : "disabled"} onChange={(event) => setRenewalEnabled((current) => ({ ...current, [node.id]: event.target.value === "enabled" }))}>
                        <option value="enabled">فعال</option>
                        <option value="disabled">غیرفعال</option>
                      </Select>
                    </FormControl>
                    <FormControl maxW={{ md: "170px" }}>
                      <FormLabel fontSize="xs" mb={1}>سهمیه تمدید</FormLabel>
                      <Input minH="44px" type="number" min={0} step={1} dir="ltr" value={remainingText} onChange={(event) => setRenewalRemaining((current) => ({ ...current, [node.id]: event.target.value }))} />
                      <FormHelperText fontSize="xs">خالی یعنی نامحدود؛ فقط تمدید واقعی مصرف می‌کند.</FormHelperText>
                    </FormControl>
                    <Button minH="44px" size="sm" colorScheme="green" variant="outline" isDisabled={remaining !== null && (!Number.isInteger(remaining) || remaining < 0)} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "renewal", enabled, remaining })}>ذخیره سیاست تمدید</Button>
                    {isOwner && node.role !== "OWNER" && (
                      <Button minH="44px" size="sm" colorScheme={node.active_owner_freeze_event_id === null ? "orange" : "green"} variant="ghost" isLoading={action.isLoading} onClick={() => {
                        const operation = node.active_owner_freeze_event_id === null ? "freeze" : "unfreeze";
                        const warning = operation === "freeze" ? `تمام زیرشاخه ${node.username} مسدود شود؟` : `مسدودی مالک برای ${node.username} رفع شود؟`;
                        if (window.confirm(warning)) action.mutate({ node, operation, reason: "Owner dashboard operation" });
                      }}>{node.active_owner_freeze_event_id === null ? "Freeze کل شاخه" : "Unfreeze کل شاخه"}</Button>
                    )}
                    {!isOwner && node.account_status === "ACTIVE" && (
                      <Button minH="44px" size="sm" colorScheme="orange" variant="ghost" isLoading={action.isLoading} onClick={() => window.confirm(`تعلیق عملیاتی شاخه ${node.username}؟`) && action.mutate({ node, operation: "suspend" })}>تعلیق شاخه</Button>
                    )}
                    {node.account_status !== "ACTIVE" && node.active_owner_freeze_event_id === null && (
                      <Button minH="44px" size="sm" colorScheme="green" variant="ghost" isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "resume" })}>رفع تعلیق عملیاتی</Button>
                    )}
                  </Stack>
                </SimpleGrid>
              )}
              {canAct && (userData.role === "OWNER" || userData.is_sudo) && (
                <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2} p={3} mt={3} bg="blackAlpha.200" borderRadius="10px">
                  <FormControl maxW={{ md: "145px" }}>
                    <FormLabel fontSize="xs" mb={1}>تعداد Trial</FormLabel>
                    <Input minH="44px" type="number" min={1} step={1} dir="ltr" value={trialAmounts[node.id] || ""} onChange={(event) => setTrialAmounts((current) => ({ ...current, [node.id]: event.target.value }))} />
                  </FormControl>
                  <FormControl flex="1">
                    <FormLabel fontSize="xs" mb={1}>دلیل تغییر سهمیه Trial</FormLabel>
                    <Input minH="44px" maxLength={512} value={trialReason} onChange={(event) => setTrialReasons((current) => ({ ...current, [node.id]: event.target.value }))} />
                  </FormControl>
                  <Button minH="44px" size="sm" colorScheme="orange" isDisabled={!Number.isInteger(trialAmount) || trialAmount <= 0 || !trialReason.trim()} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "trial-grant", amount: trialAmount, reason: trialReason.trim() })}>افزایش Trial</Button>
                  <Button minH="44px" size="sm" variant="outline" colorScheme="orange" isDisabled={!Number.isInteger(trialAmount) || trialAmount <= 0 || !trialReason.trim()} isLoading={action.isLoading} onClick={() => window.confirm(`بازپس‌گیری ${trialAmount} سهمیه Trial از ${node.username}؟`) && action.mutate({ node, operation: "trial-reclaim", amount: trialAmount, reason: trialReason.trim() })}>بازپس‌گیری Trial</Button>
                </Stack>
              )}
              {isOwner && node.role !== "OWNER" && (
                <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2} p={3} mt={3} bg="blackAlpha.200" borderRadius="10px">
                  <FormControl maxW={{ md: "180px" }}>
                    <FormLabel fontSize="xs" mb={1}>Referrer username</FormLabel>
                    <Input minH="44px" dir="ltr" value={referrer} onChange={(event) => setReferrers((current) => ({ ...current, [node.id]: event.target.value }))} />
                  </FormControl>
                  <FormControl maxW={{ md: "145px" }}>
                    <FormLabel fontSize="xs" mb={1}>Rate (bps)</FormLabel>
                    <Input minH="44px" type="number" min={0} max={10000} step={1} dir="ltr" value={referralRateText} onChange={(event) => setReferralRates((current) => ({ ...current, [node.id]: event.target.value }))} />
                  </FormControl>
                  <FormControl flex="1">
                    <FormLabel fontSize="xs" mb={1}>یادداشت attribution</FormLabel>
                    <Input minH="44px" maxLength={512} value={referralNote} onChange={(event) => setReferralNotes((current) => ({ ...current, [node.id]: event.target.value }))} />
                    <FormHelperText fontSize="xs">فقط attribution و audit؛ هیچ اعتبار یا منبعی خودکار ایجاد نمی‌شود.</FormHelperText>
                  </FormControl>
                  <Button minH="44px" size="sm" colorScheme="purple" isDisabled={!referrer.trim() || !Number.isInteger(referralRate) || referralRate < 0 || referralRate > 10000} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "referral-set", referrer: referrer.trim(), rateBps: referralRate, reason: referralNote.trim() || undefined })}>ذخیره Referral</Button>
                  <Button minH="44px" size="sm" variant="outline" colorScheme="purple" isDisabled={node.referral_referrer_admin_id === null} isLoading={action.isLoading} onClick={() => window.confirm(`Referral ${node.username} حذف شود؟`) && action.mutate({ node, operation: "referral-remove", reason: referralNote.trim() || undefined })}>حذف Referral</Button>
                </Stack>
              )}
            </Box>
          );
        })}
      </Stack>
    </Card>
  );
};
