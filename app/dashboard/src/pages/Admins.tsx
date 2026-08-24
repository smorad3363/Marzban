import {
  Alert, AlertDialog, AlertDialogBody, AlertDialogContent, AlertDialogFooter,
  AlertDialogHeader, AlertDialogOverlay, AlertIcon, Badge, Box, Button, Card,
  Checkbox, Collapse, Divider, FormControl, FormHelperText, FormLabel, HStack, IconButton, Input,
  InputGroup, InputLeftElement, Menu, MenuButton, MenuItem, MenuList, Progress, Select, SimpleGrid, Skeleton, Stack, Table,
  TableContainer, Tbody, Td, Text, Textarea, Th, Thead, Tr, VStack, chakra,
  useDisclosure, useToast,
} from "@chakra-ui/react";
import {
  EllipsisVerticalIcon, FunnelIcon, MagnifyingGlassIcon, PencilSquareIcon, PlusIcon,
  TrashIcon, UserGroupIcon,
} from "@heroicons/react/24/outline";
import { AdminFormDrawer } from "components/AdminFormDrawer";
import { AppShell } from "components/AppShell";
import useGetUser from "hooks/useGetUser";
import { FC, Fragment, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { Navigate, useSearchParams } from "react-router-dom";
import { fetch } from "service/http";
import { AdminCapabilities, ManagedAdmin, ManagedAdminList } from "types/Admin";
import { localizedApiError } from "utils/apiError";
import { formatBytes } from "utils/formatByte";

const SearchIcon = chakra(MagnifyingGlassIcon, { baseStyle: { w: 4, h: 4 } });
const AddIcon = chakra(PlusIcon, { baseStyle: { w: 4, h: 4 } });
const EditIcon = chakra(PencilSquareIcon, { baseStyle: { w: 4, h: 4 } });
const RemoveIcon = chakra(TrashIcon, { baseStyle: { w: 4, h: 4 } });
const MoreIcon = chakra(EllipsisVerticalIcon, { baseStyle: { w: 5, h: 5 } });
const AdminsIcon = chakra(UserGroupIcon, { baseStyle: { w: 5, h: 5 } });
const FilterIcon = chakra(FunnelIcon, { baseStyle: { w: 4, h: 4 } });
const PAGE_SIZE = 20;
const GIB = 1024 ** 3;

const billingModeLabels: Record<string, string> = {
  LEGACY_COMPAT: "قدیمی (فقط مهاجرت)",
  SEAT_CREDIT: "ظرفیت دستگاه قدیمی",
  USED_TRAFFIC: "مصرف واقعی",
  ALLOCATED_TRAFFIC: "حجم ساخته‌شده",
  USER_CREDIT: "حجم نامحدود · سقف اکانت",
};

const creditResource = (mode: string) => mode === "USER_CREDIT" ? "user" : mode === "SEAT_CREDIT" ? "seat" : "traffic";
const creditUnit = (mode: string) => mode === "USER_CREDIT" ? "اکانت" : mode === "SEAT_CREDIT" ? "دستگاه" : "گیگابایت";
const apiCreditAmount = (mode: string, value: number) => creditResource(mode) === "traffic" ? Math.round(value * GIB) : Math.round(value);

const statusMeta = {
  ACTIVE: { label: "فعال", scheme: "green", border: "#48d58b", background: "rgba(16, 92, 60, .18)" },
  SUSPENDED: { label: "فریز", scheme: "orange", border: "#d4af37", background: "rgba(145, 105, 22, .16)" },
  DISABLED: { label: "غیرفعال", scheme: "red", border: "#f05252", background: "rgba(127, 38, 45, .16)" },
} as const;

const CreditRemaining: FC<{ admin: ManagedAdmin }> = ({ admin }) => {
  const { t } = useTranslation();
  const quota = admin.quota;
  return (
    <Stack spacing={1.5} align="stretch" minW={{ lg: "145px" }}>
      <Text fontWeight="700" sx={{ fontVariantNumeric: "tabular-nums" }}>
        {quota.credit_remaining === null
          ? t("unlimited")
          : admin.policy.billing_mode === "SEAT_CREDIT"
            ? `${quota.credit_remaining} دستگاه`
            : admin.policy.billing_mode === "USER_CREDIT"
              ? `${quota.credit_remaining} اکانت`
            : formatBytes(quota.credit_remaining)}
      </Text>
      {quota.credit_usage_percent !== null && (
        <>
          <Progress value={Math.min(100, Math.max(0, quota.credit_usage_percent))} size="xs" colorScheme={quota.sudo_warning_active ? "orange" : "green"} bg="whiteAlpha.100" borderRadius="full" aria-label={`مصرف اعتبار ${quota.credit_usage_percent} درصد`} />
          <HStack spacing={2} justify="space-between">
          <Text fontSize="xs" color="gray.300">مصرف {quota.credit_usage_percent}%</Text>
          {quota.sudo_warning_active && <Badge colorScheme="orange" variant="subtle">{t("admins.creditWarning")}</Badge>}
          </HStack>
        </>
      )}
    </Stack>
  );
};

export const Admins: FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { userData, getUserIsPending, getUserIsSuccess } = useGetUser();
  const formDisclosure = useDisclosure();
  const deleteDisclosure = useDisclosure();
  const filtersDisclosure = useDisclosure();
  const freezeDisclosure = useDisclosure();
  const creditDisclosure = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [selected, setSelected] = useState<ManagedAdmin | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [roleFilter, setRoleFilter] = useState("");
  const [billingFilter, setBillingFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expandedUsername, setExpandedUsername] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkAmount, setBulkAmount] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [freezeTarget, setFreezeTarget] = useState<ManagedAdmin | null>(null);
  const [freezeReason, setFreezeReason] = useState("");
  const [creditTarget, setCreditTarget] = useState<ManagedAdmin | null>(null);
  const [creditOperation, setCreditOperation] = useState<"grant" | "reclaim">("grant");
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [deleteStrategy, setDeleteStrategy] = useState<"delete_users" | "disable_users" | "keep_users">("keep_users");
  const capabilities = useQuery<AdminCapabilities, Error>(
    ["admin-capabilities", userData.username],
    () => fetch("/admin/capabilities"),
    { enabled: getUserIsSuccess }
  );
  const canManage = Boolean(capabilities.data?.can_manage_admins);
  const canCreate = Boolean(capabilities.data?.can_create_admins);

  useEffect(() => {
    if (canCreate && searchParams.get("create") === "1") {
      setSelected(null);
      formDisclosure.onOpen();
      setSearchParams({}, { replace: true });
    }
  }, [canCreate, formDisclosure, searchParams, setSearchParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const query = useQuery<ManagedAdminList, Error>(
    ["admin-management", page, search, roleFilter, billingFilter, statusFilter],
    () => {
      const params = new URLSearchParams({
        offset: String(page * PAGE_SIZE),
        limit: String(PAGE_SIZE),
        username: search,
      });
      if (roleFilter) params.set("role", roleFilter);
      if (billingFilter) params.set("billing_mode", billingFilter);
      if (statusFilter) params.set("account_status", statusFilter);
      return fetch(`/admin-management?${params.toString()}`);
    },
    { keepPreviousData: true, enabled: canManage, refetchInterval: 15000 }
  );

  const removeMutation = useMutation(
    ({ username, strategy }: { username: string; strategy: typeof deleteStrategy }) =>
      fetch(`/admin/${username}`, { method: "DELETE", body: { strategy } }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-management");
        toast({ title: t("admins.deleted"), status: "success", duration: 3000 });
        deleteDisclosure.onClose();
      },
      onError: (error) => {
        toast({ title: t("admins.deleteFailed"), description: localizedApiError(error), status: "error", duration: 5000 });
      },
    }
  );

  const refreshAdminData = () => {
    queryClient.invalidateQueries("admin-management");
    queryClient.invalidateQueries("admin-hierarchy-tree");
    queryClient.invalidateQueries("account-summary");
  };

  const quickAction = useMutation(
    ({ item, operation, reason }: { item: ManagedAdmin; operation: "activate" | "freeze" | "unfreeze" | "resume" | "trial-reset"; reason?: string }) => {
      if (operation === "trial-reset") {
        return fetch(`/admin-management/${item.username}/trial-quota/reset`, {
          method: "POST",
          body: { idempotency_key: `trial-reset-${item.id}-${crypto.randomUUID()}`, note: "بازنشانی سهمیه تست توسط ادمین بالاسری" },
        });
      }
      if (operation === "resume") {
        return fetch(`/admin-management/${item.username}/resume`, { method: "POST" });
      }
      if (operation === "activate") {
        return fetch(`/admin-management/${encodeURIComponent(item.username)}/activate`, { method: "POST" });
      }
      return fetch(`/admin-management/${item.username}/${operation}`, {
        method: "POST",
        body: operation === "freeze"
          ? { reason_id: 1, idempotency_key: `freeze-${item.id}-${crypto.randomUUID()}`, note: reason }
          : { idempotency_key: `unfreeze-${item.id}-${crypto.randomUUID()}` },
      });
    },
    {
      onSuccess: () => {
        refreshAdminData();
        freezeDisclosure.onClose();
        setFreezeReason("");
        setFreezeTarget(null);
        toast({ title: "عملیات انجام شد", status: "success", duration: 2500 });
      },
      onError: (error) => { toast({ title: "عملیات انجام نشد", description: localizedApiError(error), status: "error", duration: 5000 }); },
    }
  );

  const creditMutation = useMutation(
    ({ item, operation, amount, reason }: { item: ManagedAdmin; operation: "grant" | "reclaim"; amount: number; reason?: string }) =>
      fetch(`/admin-management/${encodeURIComponent(item.username)}/credit/${operation}`, {
        method: "POST",
        body: { amount: apiCreditAmount(item.policy.billing_mode, amount), idempotency_key: `admin-credit-${crypto.randomUUID()}`, note: reason || undefined },
      }),
    {
      onSuccess: () => {
        refreshAdminData();
        creditDisclosure.onClose();
        setCreditTarget(null); setCreditAmount(""); setCreditReason("");
        toast({ title: "اعتبار به‌روزرسانی شد", status: "success", duration: 2500 });
      },
      onError: (error) => { toast({ title: "تغییر اعتبار انجام نشد", description: localizedApiError(error), status: "error", duration: 5000 }); },
    }
  );

  if (!getUserIsPending && !capabilities.isLoading && !canManage) return <Navigate to="/" replace />;

  const admins = query.data?.admins || [];
  const total = query.data?.total || 0;
  const selectedAdmins = admins.filter((item) => selectedIds.includes(item.id));
  const selectedResource = selectedAdmins[0] ? creditResource(selectedAdmins[0].policy.billing_mode) : null;
  const mixedSelection = selectedAdmins.some((item) => creditResource(item.policy.billing_mode) !== selectedResource);
  const activeFilterCount = [roleFilter, billingFilter, statusFilter].filter(Boolean).length;
  const canEdit = (item: ManagedAdmin) => item.role !== "OWNER" || item.username === userData.username;
  const canAct = (item: ManagedAdmin) => item.role !== "OWNER" && item.username !== userData.username;
  const openCreate = () => { setSelected(null); formDisclosure.onOpen(); };
  const openEdit = (item: ManagedAdmin) => { setSelected(item); formDisclosure.onOpen(); };
  const openDelete = (item: ManagedAdmin) => { setSelected(item); setDeleteStrategy("keep_users"); deleteDisclosure.onOpen(); };
  const openFreeze = (item: ManagedAdmin) => { setFreezeTarget(item); setFreezeReason(""); freezeDisclosure.onOpen(); };
  const openCredit = (item: ManagedAdmin, operation: "grant" | "reclaim") => { setCreditTarget(item); setCreditOperation(operation); setCreditAmount(""); setCreditReason(""); creditDisclosure.onOpen(); };
  const clearFilters = () => { setRoleFilter(""); setBillingFilter(""); setStatusFilter(""); setPage(0); };
  const toggleSelection = (item: ManagedAdmin, checked: boolean) => setSelectedIds((current) => checked ? [...new Set([...current, item.id])] : current.filter((id) => id !== item.id));
  const renderStatusAction = (item: ManagedAdmin, compact = false) => {
    if (!canAct(item)) return null;
    if (item.account_status === "SUSPENDED") return <Button minH={compact ? "40px" : "36px"} size={compact ? "sm" : "xs"} variant="ghost" colorScheme="blue" isLoading={quickAction.isLoading} onClick={() => quickAction.mutate({ item, operation: item.active_owner_freeze_event_id ? "unfreeze" : "resume" })}>رفع فریز</Button>;
    if (item.account_status === "DISABLED") return <Button minH={compact ? "40px" : "36px"} size={compact ? "sm" : "xs"} variant="ghost" colorScheme="green" isLoading={quickAction.isLoading} onClick={() => window.confirm(`ادمین ${item.username} فعال شود؟`) && quickAction.mutate({ item, operation: "activate" })}>فعال‌سازی</Button>;
    return <Button minH={compact ? "40px" : "36px"} size={compact ? "sm" : "xs"} variant="ghost" colorScheme="orange" isLoading={quickAction.isLoading} onClick={() => openFreeze(item)}>فریز</Button>;
  };
  const renderMoreActions = (item: ManagedAdmin, includeManageActions = false) => {
    const hasTrialReset = canAct(item) && item.trial_quota_limit > 0;
    if (!hasTrialReset && !includeManageActions) return null;
    return (
      <Menu placement="bottom-end">
        <MenuButton as={IconButton} aria-label={`عملیات بیشتر ${item.username}`} icon={<MoreIcon />} size="sm" minW={includeManageActions ? "44px" : "36px"} h={includeManageActions ? "44px" : "36px"} variant="ghost" />
        <MenuList minW="190px" bg="var(--panel-surface)" borderColor="var(--panel-border)" boxShadow="xl" zIndex={20}>
          {hasTrialReset && <MenuItem bg="transparent" _hover={{ bg: "whiteAlpha.100" }} onClick={() => window.confirm(`تعداد تست قابل ساخت ${item.username} به ${item.trial_quota_limit} برگردد؟`) && quickAction.mutate({ item, operation: "trial-reset" })}>ریست اکانت تست قابل ساخت</MenuItem>}
          {includeManageActions && <MenuItem bg="transparent" _hover={{ bg: "whiteAlpha.100" }} isDisabled={!canEdit(item)} onClick={() => openEdit(item)}>ویرایش ادمین</MenuItem>}
          {includeManageActions && item.role !== "OWNER" && <MenuItem color="red.300" bg="transparent" _hover={{ bg: "whiteAlpha.100" }} onClick={() => openDelete(item)}>حذف ادمین</MenuItem>}
        </MenuList>
      </Menu>
    );
  };
  const runBulk = async (operation: "grant_credit" | "reclaim_credit") => {
    const numeric = Number(bulkAmount);
    if (!selectedAdmins.length || mixedSelection || !Number.isFinite(numeric) || numeric <= 0) return;
    setBulkBusy(true);
    try {
      const operationId = `bulk-admin-${crypto.randomUUID()}`;
      await fetch("/admin-management/bulk-credit/jobs", {
        method: "POST",
        body: { operation_id: operationId, operation, selected_admin_ids: selectedIds, amount: apiCreditAmount(selectedAdmins[0].policy.billing_mode, numeric) },
      });
      let result = await fetch<{ has_more: boolean; success: number; failed: number; skipped: number }>(`/admin-management/bulk-credit/jobs/${operationId}/execute`, { method: "POST", body: { chunk_size: 100 } });
      while (result.has_more) result = await fetch(`/admin-management/bulk-credit/jobs/${operationId}/execute`, { method: "POST", body: { chunk_size: 100 } });
      refreshAdminData();
      setBulkAmount("");
      toast({ title: `${result.success} انجام شد · ${result.failed + result.skipped} انجام نشد`, status: result.failed ? "warning" : "success" });
    } catch (error) {
      toast({ title: "عملیات گروهی انجام نشد", description: localizedApiError(error), status: "error" });
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <AppShell>
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "center" }} mb={5} gap={4}>
        <Box>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em">{t("admins.title")}</Text>
          <Text color="gray.300" mt={1} maxW="650px">{t("admins.subtitle")}</Text>
        </Box>
        {canCreate && <Button minH="40px" flexShrink={0} colorScheme="primary" color="#07130e" leftIcon={<AddIcon />} onClick={openCreate}>{t("admins.create")}</Button>}
      </Stack>

      <Card variant="outline" bg="#111d17" color="gray.100" borderRadius={{ base: "16px", md: "20px" }} borderColor="#33483b" boxShadow="panel" overflow="hidden">
        <Stack direction={{ base: "column", md: "row" }} p={{ base: 3, md: 4 }} justify="space-between" align={{ md: "center" }} borderBottomWidth="1px" borderColor="#33483b" gap={3}>
          <Box>
            <Text as="h2" fontWeight="800">فهرست ادمین‌ها</Text>
            <Text mt={1} fontSize="xs" color="gray.400">اطلاعات اصلی هر ادمین را می‌بینید. برای بقیه موارد، جزئیات را باز کنید.</Text>
          </Box>
          <Stack direction={{ base: "column", sm: "row" }} w={{ base: "full", md: "auto" }} spacing={2}>
            <InputGroup flex="1" minW={{ base: 0, md: "260px" }} maxW={{ md: "360px" }}>
              <InputLeftElement pointerEvents="none" color="gray.400"><SearchIcon /></InputLeftElement>
              <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("admins.search")} />
            </InputGroup>
            <Button w={{ base: "full", sm: "auto" }} minH="40px" variant="outline" leftIcon={<FilterIcon />} onClick={filtersDisclosure.onToggle} aria-expanded={filtersDisclosure.isOpen}>فیلترها{activeFilterCount ? ` (${activeFilterCount})` : ""}</Button>
          </Stack>
        </Stack>

        <Collapse in={filtersDisclosure.isOpen} animateOpacity>
          <SimpleGrid columns={{ base: 1, sm: 3 }} gap={2} p={3} bg="var(--panel-nested)" borderBottomWidth="1px" borderColor="var(--panel-border)">
            <Select aria-label="فیلتر نقش" value={roleFilter} size="sm" onChange={(event) => { setRoleFilter(event.target.value); setPage(0); }}><option value="">همه نقش‌ها</option><option value="SUPER_ADMIN">سوپر ادمین</option><option value="ADMIN">ادمین</option></Select>
            <Select aria-label="فیلتر نوع اعتبار" value={billingFilter} size="sm" onChange={(event) => { setBillingFilter(event.target.value); setPage(0); }}><option value="">همه اعتبارها</option><option value="USED_TRAFFIC">مصرف واقعی</option><option value="ALLOCATED_TRAFFIC">حجم ساخته‌شده</option><option value="USER_CREDIT">نامحدود با سقف اکانت</option></Select>
            <HStack><Select aria-label="فیلتر وضعیت" value={statusFilter} size="sm" onChange={(event) => { setStatusFilter(event.target.value); setPage(0); }}><option value="">همه وضعیت‌ها</option><option value="ACTIVE">فعال</option><option value="SUSPENDED">فریز</option><option value="DISABLED">غیرفعال</option></Select>{activeFilterCount > 0 && <Button size="sm" variant="ghost" onClick={clearFilters}>پاک‌کردن</Button>}</HStack>
          </SimpleGrid>
        </Collapse>

        {selectedAdmins.length > 0 && (
          <HStack p={3} bg="rgba(212,175,55,.08)" borderBottomWidth="1px" borderColor="var(--panel-border)" flexWrap="wrap">
            <Badge colorScheme={mixedSelection ? "red" : "yellow"}>{selectedAdmins.length} انتخاب</Badge>
            {mixedSelection ? <Text fontSize="xs" color="red.200">برای عملیات گروهی، واحد اعتبار باید یکسان باشد.</Text> : <>
              <Input type="number" min={1} step={selectedResource === "traffic" ? 0.1 : 1} value={bulkAmount} onChange={(event) => setBulkAmount(event.target.value)} placeholder={`مقدار (${creditUnit(selectedAdmins[0].policy.billing_mode)})`} maxW="180px" size="sm" />
              <Button size="sm" colorScheme="primary" isLoading={bulkBusy} isDisabled={Number(bulkAmount) <= 0} onClick={() => runBulk("grant_credit")}>افزودن</Button>
              <Button size="sm" variant="outline" isLoading={bulkBusy} isDisabled={Number(bulkAmount) <= 0} onClick={() => runBulk("reclaim_credit")}>پس‌گرفتن</Button>
            </>}
            <Button size="xs" ms="auto" variant="ghost" onClick={() => setSelectedIds([])}>لغو انتخاب</Button>
          </HStack>
        )}

        {query.isError && <Alert status="error" m={4} w="auto"><AlertIcon />{t("admins.loadFailed")}<Button ms="auto" size="sm" onClick={() => query.refetch()}>{t("retry")}</Button></Alert>}

        {query.isLoading ? (
          <Stack p={5}>{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} startColor="#16251c" endColor="#24392d" height="54px" borderRadius="8px" />)}</Stack>
        ) : admins.length === 0 ? (
          <VStack py={16} px={5} spacing={3}>
            <Box p={3} color="primary.300" borderRadius="full" bg="rgba(72, 213, 139, .12)"><AdminsIcon /></Box>
            <Text color="white" fontWeight="700">{t("admins.empty")}</Text>
            <Text color="gray.400" fontSize="sm" textAlign="center">{t(search ? "admins.emptySearch" : "admins.emptyHelp")}</Text>
          </VStack>
        ) : (
          <>
            <TableContainer display={{ base: "none", lg: "block" }}>
              <Table size="sm">
                <Thead bg="rgba(4, 14, 11, .46)"><Tr><Th w="24%">{t("admins.admin")}</Th><Th w="24%">{t("admins.access")}</Th><Th w="20%">خلاصه اعتبار</Th><Th textAlign="end">{t("admins.actions")}</Th></Tr></Thead>
                <Tbody>{admins.map((item) => (
                  <Fragment key={item.username}>
                    <Tr bg={expandedUsername === item.username ? "rgba(255,255,255,.055)" : statusMeta[item.account_status].background} _hover={{ bg: expandedUsername === item.username ? "rgba(255,255,255,.065)" : "rgba(255,255,255,.045)" }} transition="background-color 160ms ease">
                      <Td borderInlineStartWidth="3px" borderInlineStartColor={statusMeta[item.account_status].border}>
                        <HStack align="start" spacing={3}>
                          {canAct(item) && <Checkbox mt={1} aria-label={`انتخاب ${item.username}`} isChecked={selectedIds.includes(item.id)} onChange={(event) => toggleSelection(item, event.target.checked)} />}
                          <Box minW={0}><HStack spacing={2} flexWrap="wrap"><Text color="white" fontWeight="750" dir="ltr">{item.username}</Text><Badge colorScheme={statusMeta[item.account_status].scheme}>{statusMeta[item.account_status].label}</Badge></HStack><Text mt={1} fontSize="xs" color="gray.300">زیرمجموعهٔ: <Text as="span" dir="ltr">{item.parent_username || "—"}</Text></Text></Box>
                        </HStack>
                      </Td>
                      <Td>
                        <Stack align="start" spacing={1.5}>
                          <HStack flexWrap="wrap"><Badge colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge><Badge variant="outline">{billingModeLabels[item.policy.billing_mode] || item.policy.billing_mode}</Badge></HStack>
                          <Text fontSize="xs" color="gray.300">کاربران: <Text as="span" color="white" fontWeight="700" sx={{ fontVariantNumeric: "tabular-nums" }}>{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Text></Text>
                          <Text fontSize="xs" color="gray.400">{item.user_creation_mode === "PLAN_ONLY" ? "ساخت کاربر فقط از پلن" : "ساخت کاربر سفارشی"}</Text>
                        </Stack>
                      </Td>
                      <Td><CreditRemaining admin={item} /></Td>
                      <Td>
                        <HStack justify="end" spacing={1} flexWrap="wrap">
                          <Button size="xs" variant="ghost" minH="36px" aria-expanded={expandedUsername === item.username} onClick={() => setExpandedUsername((current) => current === item.username ? null : item.username)}>{expandedUsername === item.username ? "بستن" : "جزئیات"}</Button>
                          {canAct(item) && <Button minH="36px" size="xs" variant="ghost" colorScheme="red" onClick={() => openCredit(item, "reclaim")}>کاهش</Button>}
                          {renderStatusAction(item)}
                          {canAct(item) && <Button minH="36px" size="xs" variant="ghost" colorScheme="green" onClick={() => openCredit(item, "grant")}>افزایش</Button>}
                          {renderMoreActions(item)}
                          <IconButton aria-label={`ویرایش ${item.username}`} minW="36px" h="36px" size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} />
                          <IconButton aria-label={`حذف ${item.username}`} minW="36px" h="36px" size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.role === "OWNER"} onClick={() => openDelete(item)} />
                        </HStack>
                      </Td>
                    </Tr>
                    {expandedUsername === item.username && (
                      <Tr bg="blackAlpha.200">
                        <Td colSpan={4} py={4}>
                          <SimpleGrid columns={{ base: 2, xl: 4 }} gap={4}>
                            <Box><Text color="gray.400" fontSize="xs">{t("admins.operationRemaining")}</Text><Text mt={1}>{item.quota.operation_allowance_remaining ?? t("unlimited")}</Text></Box>
                            <Box><Text color="gray.400" fontSize="xs">{t("admins.maxDuration")}</Text><Text mt={1}>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Text></Box>
                            <Box><Text color="gray.400" fontSize="xs">{t("admins.expiryDate")}</Text><Text mt={1} dir="ltr">{item.policy.expiry_date || t("unlimited")}</Text></Box>
                            <Box><Text color="gray.400" fontSize="xs">{t("admins.telegramId")}</Text><Text mt={1} dir="ltr">{item.telegram_id ?? t("admins.noContact")}</Text></Box>
                          </SimpleGrid>
                        </Td>
                      </Tr>
                    )}
                  </Fragment>
                ))}</Tbody>
              </Table>
            </TableContainer>

            <Stack display={{ base: "flex", lg: "none" }} divider={<Divider borderColor="#33483b" />} spacing={0}>
              {admins.map((item) => (
                <Box key={item.username} p={3} bg={statusMeta[item.account_status].background} borderInlineStartWidth="3px" borderInlineStartColor={statusMeta[item.account_status].border}>
                  <HStack justify="space-between" align="start">
                    <HStack align="start" spacing={2}>{canAct(item) && <Checkbox mt={1} aria-label={`انتخاب ${item.username}`} isChecked={selectedIds.includes(item.id)} onChange={(event) => toggleSelection(item, event.target.checked)} />}<Box minW={0}><HStack spacing={2} flexWrap="wrap"><Text color="white" fontWeight="750" dir="ltr">{item.username}</Text><Badge colorScheme={statusMeta[item.account_status].scheme}>{statusMeta[item.account_status].label}</Badge></HStack><Text mt={1} fontSize="xs" color="gray.300">زیرمجموعهٔ: <Text as="span" dir="ltr">{item.parent_username || "—"}</Text></Text></Box></HStack>
                    {renderMoreActions(item, true)}
                  </HStack>
                  <SimpleGrid columns={2} gap={2} mt={3} fontSize="sm">
                    <Box p={2.5} bg="rgba(0,0,0,.16)" borderRadius="10px"><Text color="gray.400" fontSize="xs">دسترسی</Text><HStack mt={1.5} spacing={1} flexWrap="wrap"><Badge colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge><Badge variant="outline">{billingModeLabels[item.policy.billing_mode] || item.policy.billing_mode}</Badge></HStack><Text mt={2} color="gray.300" fontSize="xs">کاربران: <Text as="span" color="white" fontWeight="700">{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Text></Text><Text mt={1} color="gray.400" fontSize="xs">{item.user_creation_mode === "PLAN_ONLY" ? "فقط از پلن" : "ساخت سفارشی"}</Text></Box>
                    <Box p={2.5} bg="rgba(0,0,0,.16)" borderRadius="10px"><Text color="gray.400" fontSize="xs">{t("admins.creditRemaining")}</Text><Box mt={1.5}><CreditRemaining admin={item} /></Box></Box>
                  </SimpleGrid>
                  <HStack mt={3} spacing={1} flexWrap="wrap">
                    <Button minH="44px" size="sm" flex="1" variant="ghost" aria-expanded={expandedUsername === item.username} onClick={() => setExpandedUsername((current) => current === item.username ? null : item.username)}>{expandedUsername === item.username ? "بستن جزئیات" : "جزئیات"}</Button>
                    {canAct(item) && <Button minH="44px" size="sm" variant="ghost" colorScheme="red" onClick={() => openCredit(item, "reclaim")}>کاهش</Button>}
                    {renderStatusAction(item, true)}
                    {canAct(item) && <Button minH="44px" size="sm" variant="ghost" colorScheme="green" onClick={() => openCredit(item, "grant")}>افزایش</Button>}
                  </HStack>
                  {expandedUsername === item.username && (
                    <SimpleGrid columns={2} gap={3} mt={3} pt={3} borderTopWidth="1px" borderColor="#33483b" fontSize="sm">
                      <Box><Text color="gray.400" fontSize="xs">{t("admins.operationRemaining")}</Text><Text color="gray.100" mt={1}>{item.quota.operation_allowance_remaining ?? t("unlimited")}</Text></Box>
                      <Box><Text color="gray.400" fontSize="xs">{t("admins.maxDuration")}</Text><Text color="gray.100" mt={1}>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Text></Box>
                      <Box><Text color="gray.400" fontSize="xs">{t("admins.expiryDate")}</Text><Text color="gray.100" mt={1} dir="ltr">{item.policy.expiry_date || t("unlimited")}</Text></Box>
                      <Box><Text color="gray.400" fontSize="xs">{t("admins.telegramId")}</Text><Text color="gray.100" mt={1} dir="ltr">{item.telegram_id ?? t("admins.noContact")}</Text></Box>
                    </SimpleGrid>
                  )}
                </Box>
              ))}
            </Stack>
          </>
        )}

        {total > PAGE_SIZE && (
          <HStack justify="space-between" p={4} borderTopWidth="1px" borderColor="#33483b">
            <Text fontSize="sm" color="gray.400">{t("admins.page", { current: page + 1, total: Math.ceil(total / PAGE_SIZE) })}</Text>
            <HStack><Button size="sm" variant="outline" borderColor="#475f50" isDisabled={page === 0} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button><Button size="sm" variant="outline" borderColor="#475f50" isDisabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button></HStack>
          </HStack>
        )}
      </Card>

      <AdminFormDrawer isOpen={formDisclosure.isOpen} admin={selected} onClose={formDisclosure.onClose} />
      <AlertDialog isOpen={deleteDisclosure.isOpen} leastDestructiveRef={cancelRef} onClose={deleteDisclosure.onClose}>
        <AlertDialogOverlay bg="rgba(0, 0, 0, .72)">
          <AlertDialogContent bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
            <AlertDialogHeader>{t("admins.deleteTitle")}</AlertDialogHeader>
            <AlertDialogBody>
              <Text mb={3}>{t("admins.deleteConfirm", { username: selected?.username })}</Text>
              <FormControl>
                <FormLabel>{t("admins.deleteStrategy")}</FormLabel>
                <Select value={deleteStrategy} onChange={(event) => setDeleteStrategy(event.target.value as typeof deleteStrategy)}>
                  <option value="keep_users">{t("admins.keepUsers")}</option>
                  <option value="disable_users">{t("admins.disableUsers")}</option>
                  <option value="delete_users">{t("admins.deleteUsers")}</option>
                </Select>
                <FormHelperText>{t(`admins.deleteStrategyHelp.${deleteStrategy}`)}</FormHelperText>
              </FormControl>
            </AlertDialogBody>
            <AlertDialogFooter borderTopWidth="1px" borderColor="#33483b" gap={3}>
              <Button ref={cancelRef} variant="ghost" onClick={deleteDisclosure.onClose}>{t("cancel")}</Button>
              <Button colorScheme="red" isLoading={removeMutation.isLoading} onClick={() => selected && removeMutation.mutate({ username: selected.username, strategy: deleteStrategy })}>{t("delete")}</Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
      <AlertDialog isOpen={freezeDisclosure.isOpen} leastDestructiveRef={cancelRef} onClose={freezeDisclosure.onClose}>
        <AlertDialogOverlay bg="rgba(0, 0, 0, .76)">
          <AlertDialogContent bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px">
            <AlertDialogHeader>فریز {freezeTarget?.username}</AlertDialogHeader>
            <AlertDialogBody>
              <FormControl isRequired>
                <FormLabel>دلیل فریز</FormLabel>
                <Textarea autoFocus maxLength={512} value={freezeReason} onChange={(event) => setFreezeReason(event.target.value)} placeholder="دلیل قابل نمایش برای این ادمین را بنویسید" />
                <FormHelperText>این متن در حساب ادمین و گزارش فعالیت ثبت می‌شود.</FormHelperText>
              </FormControl>
            </AlertDialogBody>
            <AlertDialogFooter gap={3} borderTopWidth="1px" borderColor="var(--panel-border)">
              <Button ref={cancelRef} variant="ghost" onClick={freezeDisclosure.onClose}>انصراف</Button>
              <Button colorScheme="orange" isLoading={quickAction.isLoading} isDisabled={!freezeReason.trim()} onClick={() => freezeTarget && quickAction.mutate({ item: freezeTarget, operation: "freeze", reason: freezeReason.trim() })}>فریز ادمین و زیرشاخه</Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
      <AlertDialog isOpen={creditDisclosure.isOpen} leastDestructiveRef={cancelRef} onClose={creditDisclosure.onClose}>
        <AlertDialogOverlay bg="rgba(0, 0, 0, .76)">
          <AlertDialogContent bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px">
            <AlertDialogHeader>{creditOperation === "grant" ? "افزایش" : "کاهش"} اعتبار {creditTarget?.username}</AlertDialogHeader>
            <AlertDialogBody>
              <Stack spacing={3}>
                <FormControl isRequired><FormLabel>مقدار ({creditTarget ? creditUnit(creditTarget.policy.billing_mode) : ""})</FormLabel><Input autoFocus type="number" min={creditTarget && creditResource(creditTarget.policy.billing_mode) === "traffic" ? 0.01 : 1} step={creditTarget && creditResource(creditTarget.policy.billing_mode) === "traffic" ? 0.01 : 1} dir="ltr" value={creditAmount} onChange={(event) => setCreditAmount(event.target.value)} /></FormControl>
                <FormControl><FormLabel>یادداشت اختیاری</FormLabel><Input maxLength={512} value={creditReason} onChange={(event) => setCreditReason(event.target.value)} /></FormControl>
              </Stack>
            </AlertDialogBody>
            <AlertDialogFooter gap={3} borderTopWidth="1px" borderColor="var(--panel-border)">
              <Button ref={cancelRef} variant="ghost" onClick={creditDisclosure.onClose}>انصراف</Button>
              <Button colorScheme={creditOperation === "grant" ? "green" : "red"} isLoading={creditMutation.isLoading} isDisabled={!creditTarget || !Number.isFinite(Number(creditAmount)) || Number(creditAmount) <= 0 || (creditTarget && creditResource(creditTarget.policy.billing_mode) !== "traffic" && !Number.isInteger(Number(creditAmount)))} onClick={() => creditTarget && creditMutation.mutate({ item: creditTarget, operation: creditOperation, amount: Number(creditAmount), reason: creditReason.trim() })}>{creditOperation === "grant" ? "افزایش اعتبار" : "کاهش اعتبار"}</Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>
    </AppShell>
  );
};

export default Admins;
