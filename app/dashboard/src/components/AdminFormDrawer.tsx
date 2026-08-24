import {
  Accordion, AccordionButton, AccordionIcon, AccordionItem, AccordionPanel,
  Alert, AlertIcon, Badge, Box, Button, Checkbox, Drawer, DrawerBody,
  DrawerCloseButton, DrawerContent, DrawerFooter, DrawerHeader, DrawerOverlay,
  Flex, FormControl, FormHelperText, FormLabel, HStack, Input, Select,
  SimpleGrid, Skeleton, Stack, Switch, Tag, TagCloseButton, TagLabel, Text,
  useToast,
} from "@chakra-ui/react";
import { useDashboard } from "contexts/DashboardContext";
import { ChangeEvent, FC, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import {
  AdminCapabilities, AdminPolicy, ManagedAdmin, ManagedAdminList, ManagedAdminPayload,
  PlanCategory, SubscriptionMode,
} from "types/Admin";
import { localizedApiError } from "utils/apiError";
import { formatBytes } from "utils/formatByte";

const GIB = 1024 ** 3;
type BillingMode = AdminPolicy["billing_mode"];

const billingLabels: Record<BillingMode, { title: string; help: string }> = {
  USED_TRAFFIC: { title: "مصرف واقعی", help: "اعتبار با مصرف واقعی کاربران این شاخه کم می‌شود." },
  ALLOCATED_TRAFFIC: { title: "حجم ساخته‌شده", help: "اعتبار هنگام اختصاص حجم به کاربر کم می‌شود." },
  USER_CREDIT: { title: "حجم نامحدود · سقف اکانت", help: "حجم نامحدود است و محدودیت با تعداد اکانت محاسبه می‌شود." },
  LEGACY_COMPAT: { title: "حالت قدیمی", help: "فقط برای مشاهده ادمین‌های مهاجرت‌داده‌شده." },
  SEAT_CREDIT: { title: "اعتبار دستگاه قدیمی", help: "فقط برای سازگاری رکوردهای قبلی." },
};

const advancedPolicyOptions = [
  { key: "prevent_user_creation", label: "admins.preventCreate", help: "admins.preventCreateHelp" },
  { key: "prevent_user_deletion", label: "admins.preventDelete", help: "admins.preventDeleteHelp" },
  { key: "prevent_user_reset", label: "admins.preventReset", help: "admins.preventResetHelp" },
  { key: "prevent_revoke_subscription", label: "admins.preventRevoke", help: "admins.preventRevokeHelp" },
  { key: "prevent_unlimited_traffic", label: "admins.preventUnlimited", help: "admins.preventUnlimitedHelp" },
] as const;

const emptyPolicy = (): AdminPolicy => ({
  billing_mode: "USED_TRAFFIC", total_traffic: null, expiry_date: null,
  user_limit: null, max_users: null, device_capacity_limit: null,
  admin_traffic_warning_percent: 80, sudo_traffic_warning_percent: 80,
  all_inbounds: true, allowed_inbounds: [], all_user_limits: true,
  allowed_user_limits: [], allowed_subscription_modes: [
    "limited_traffic_unlimited_devices", "unlimited_traffic_limited_devices",
    "limited_traffic_limited_devices",
  ],
  view_full_client_ip: false, max_user_duration_days: null,
  calculate_volume: "used_traffic", prevent_user_creation: false,
  prevent_user_deletion: false, prevent_user_reset: false,
  prevent_revoke_subscription: false, prevent_unlimited_traffic: false,
});

const emptyAdmin = (): ManagedAdminPayload => ({
  username: "", password: "", is_sudo: false, role: "ADMIN",
  telegram_id: null, phone: "", discord_webhook: null,
  policy: emptyPolicy(), plan_category_ids: [], can_create_admins: false,
  user_creation_mode: "PLAN_ONLY", can_manage_plans: false,
  can_delegate_admin_creation: false, can_create_allocated_children: true,
  admin_creation_limit: 0,
});

const Section: FC<{ title: string; description?: string; children: ReactNode }> = ({ title, description, children }) => (
  <Box p={{ base: 3, md: 4 }} bg="var(--panel-nested)" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="12px">
    <Text as="h3" fontWeight="800" fontSize="sm">{title}</Text>
    {description && <Text color="gray.400" fontSize="xs" mt={1}>{description}</Text>}
    <Box mt={4}>{children}</Box>
  </Box>
);

type Props = { isOpen: boolean; admin: ManagedAdmin | null; onClose: () => void };

export const AdminFormDrawer: FC<Props> = ({ isOpen, admin, onClose }) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { inbounds } = useDashboard();
  const usernameRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<ManagedAdminPayload>(emptyAdmin());
  const [billingMode, setBillingMode] = useState<BillingMode | "">("");
  const [inboundSearch, setInboundSearch] = useState("");
  const [newUserLimit, setNewUserLimit] = useState("");
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const isEditing = Boolean(admin);

  const capabilitiesQuery = useQuery<AdminCapabilities, Error>(
    "admin-capabilities", () => fetch("/admin/capabilities"),
    { enabled: isOpen, staleTime: 15000 }
  );
  const categoriesQuery = useQuery<PlanCategory[], Error>(
    "plan-categories", () => fetch("/plan-categories"),
    { enabled: isOpen, staleTime: 30000 }
  );

  useEffect(() => {
    if (admin) {
      setForm({
        username: admin.username, password: "", is_sudo: admin.is_sudo,
        role: admin.role, telegram_id: admin.telegram_id, phone: admin.phone,
        discord_webhook: admin.discord_webhook, policy: { ...admin.policy },
        plan_category_ids: [...admin.plan_category_ids],
        user_creation_mode: admin.user_creation_mode,
        can_manage_plans: admin.can_manage_plans,
        can_create_admins: admin.can_create_admins,
        can_delegate_admin_creation: admin.can_delegate_admin_creation,
        can_create_allocated_children: admin.can_create_allocated_children,
        admin_creation_limit: admin.admin_creation_limit,
      });
      setBillingMode(admin.policy.billing_mode);
    } else {
      setForm(emptyAdmin());
      setBillingMode("");
    }
    setInboundSearch(""); setNewUserLimit(""); setCreditAmount(""); setCreditReason("");
    setCreditBalance(admin?.quota.credit_remaining ?? null);
  }, [admin, isOpen]);

  const availableInbounds = useMemo(() => [...inbounds.values()].flat().filter((item) =>
    item.tag.toLocaleLowerCase().includes(inboundSearch.trim().toLocaleLowerCase())
  ), [inbounds, inboundSearch]);

  const mutation = useMutation<ManagedAdmin, Error, ManagedAdminPayload>((payload) => fetch(
    isEditing ? `/admin-management/${admin?.username}` : "/admin-management",
    { method: isEditing ? "PUT" : "POST", body: payload }
  ), {
    onSuccess: (savedAdmin) => {
      if (isEditing) {
        queryClient.setQueriesData<ManagedAdminList | undefined>("admin-management", (current) => current ? ({
          ...current,
          admins: current.admins.map((item) => item.id === savedAdmin.id ? savedAdmin : item),
        }) : current);
      }
      queryClient.invalidateQueries("admin-management");
      queryClient.invalidateQueries("admin-hierarchy-tree");
      queryClient.invalidateQueries("admin-capabilities");
      toast({ title: t(isEditing ? "admins.updated" : "admins.created"), status: "success", duration: 3000 });
      onClose();
    },
    onError: (error) => { toast({ title: t("admins.saveFailed"), description: localizedApiError(error), status: "error", duration: 5000 }); },
  });

  const creditMutation = useMutation<unknown, Error, { operation: "grant" | "reclaim"; amount: number }>(
    ({ operation, amount }) => fetch(`/admin-management/${encodeURIComponent(admin?.username || "")}/credit/${operation}`, {
      method: "POST",
      body: { amount, idempotency_key: `admin-credit-${crypto.randomUUID()}`, note: creditReason.trim() || undefined },
    }), {
      onSuccess: () => {
        setCreditAmount(""); setCreditReason("");
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("admin-hierarchy-tree");
        toast({ title: "اعتبار به‌روزرسانی شد", status: "success", duration: 3000 });
      },
      onError: (error) => { toast({ title: "تغییر اعتبار انجام نشد", description: localizedApiError(error), status: "error", duration: 5000 }); },
    }
  );

  const setField = <K extends keyof ManagedAdminPayload>(key: K, value: ManagedAdminPayload[K]) => setForm((current) => ({ ...current, [key]: value }));
  const setPolicy = <K extends keyof AdminPolicy>(key: K, value: AdminPolicy[K]) => setForm((current) => ({ ...current, policy: { ...current.policy, [key]: value } }));
  const nullableNumber = (event: ChangeEvent<HTMLInputElement>) => event.target.value === "" ? null : Number(event.target.value);

  const selectBillingMode = (mode: BillingMode | "") => {
    setBillingMode(mode);
    if (!mode) return;
    setForm((current) => ({
      ...current,
      can_create_allocated_children: mode === "USED_TRAFFIC" && current.can_create_allocated_children,
      policy: {
        ...current.policy, billing_mode: mode,
        calculate_volume: mode === "ALLOCATED_TRAFFIC" ? "created_traffic" : "used_traffic",
        total_traffic: null, max_users: null, device_capacity_limit: null,
      },
    }));
  };

  const showWarning = (title: string) => { toast({ title, status: "warning", duration: 3000 }); return false; };
  const validate = () => {
    if (!form.username.trim()) return showWarning("نام کاربری را وارد کنید");
    if (!isEditing && !form.password) return showWarning(t("admins.passwordRequired"));
    if (form.phone && !/^09\d{9}$/.test(form.phone)) return showWarning("شماره تلفن باید با فرمت 09xxxxxxxxx باشد");
    if (!isEditing && !billingMode) return showWarning("نوع حساب فرزند را انتخاب کنید");
    if (!isEditing && billingMode === "USER_CREDIT" && !form.policy.max_users) return showWarning("تعداد اکانت قابل ساخت را وارد کنید");
    if (!form.policy.all_inbounds && !form.policy.allowed_inbounds.length) return showWarning(t("admins.selectInboundRequired"));
    if (!form.policy.all_user_limits && !form.policy.allowed_user_limits.length) return showWarning(t("admins.selectUserLimitRequired"));
    if (!form.policy.allowed_subscription_modes.length) return showWarning(t("admins.selectSubscriptionModeRequired"));
    return true;
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!validate()) return;
    const payload = { ...form, phone: form.phone?.trim() || null };
    if (isEditing && !payload.password) delete payload.password;
    mutation.mutate(payload);
  };

  const toggleInbound = (tag: string, checked: boolean) => setPolicy("allowed_inbounds", (checked
    ? [...new Set([...form.policy.allowed_inbounds, tag])]
    : form.policy.allowed_inbounds.filter((value) => value !== tag)).sort());
  const addUserLimit = () => {
    const value = Number(newUserLimit);
    if (!Number.isInteger(value) || value < 1) return;
    setPolicy("allowed_user_limits", [...new Set([...form.policy.allowed_user_limits, value])].sort((a, b) => a - b));
    setNewUserLimit("");
  };
  const togglePlanCategory = (id: number, checked: boolean) => setField("plan_category_ids", checked
    ? [...new Set([...form.plan_category_ids, id])]
    : form.plan_category_ids.filter((value) => value !== id));
  const toggleSubscriptionMode = (mode: SubscriptionMode, checked: boolean) => setPolicy("allowed_subscription_modes", checked
    ? [...new Set([...form.policy.allowed_subscription_modes, mode])]
    : form.policy.allowed_subscription_modes.filter((value) => value !== mode));

  const mode = billingMode || form.policy.billing_mode;
  const accountUnit = mode === "USER_CREDIT" ? "اکانت" : mode === "SEAT_CREDIT" ? "دستگاه" : "گیگابایت";
  const parsedCreditAmount = Number(creditAmount);
  const creditAmountValid = Number.isFinite(parsedCreditAmount) && parsedCreditAmount > 0 && (!(["USER_CREDIT", "SEAT_CREDIT"].includes(mode)) || Number.isInteger(parsedCreditAmount));
  const adjustCredit = (operation: "grant" | "reclaim") => {
    if (!creditAmountValid || !admin) return;
    if (operation === "reclaim" && !window.confirm(`اعتبار ${admin.username} کم شود؟`)) return;
    creditMutation.mutate({ operation, amount: ["USER_CREDIT", "SEAT_CREDIT"].includes(mode) ? parsedCreditAmount : Math.round(parsedCreditAmount * GIB) });
  };
  const displayedBalance = creditBalance === null ? "نامحدود" : ["USER_CREDIT", "SEAT_CREDIT"].includes(mode) ? `${creditBalance} ${accountUnit}` : formatBytes(creditBalance);
  const allowedModes = capabilitiesQuery.data?.allowed_child_billing_modes || [];
  const allowedRoles = capabilitiesQuery.data?.allowed_child_roles || ["ADMIN"];
  const subscriptionModes: SubscriptionMode[] = [
    "limited_traffic_unlimited_devices", "unlimited_traffic_limited_devices",
    "limited_traffic_limited_devices", "unlimited_traffic_unlimited_devices",
  ];

  return (
    <Drawer isOpen={isOpen} onClose={onClose} placement={i18n.dir() === "rtl" ? "right" : "left"} size="full" initialFocusRef={usernameRef}>
      <DrawerOverlay bg="rgba(0,0,0,.72)" backdropFilter="blur(3px)" />
      <DrawerContent as="form" onSubmit={submit} dir={i18n.dir()} ms="auto" w="full" maxW={{ base: "100vw", lg: "940px" }} h="100dvh" bg="var(--panel-surface)" color="gray.100" borderInlineStartWidth={{ lg: "1px" }} borderColor="var(--panel-border)">
        <DrawerHeader px={{ base: 4, md: 5 }} py={4} borderBottomWidth="1px" borderColor="var(--panel-border)">
          <DrawerCloseButton top={4} insetInlineEnd={4} />
          <Box pe={12}><Text fontSize="lg" fontWeight="800">{t(isEditing ? "admins.editTitle" : "admins.createTitle")}</Text><Text mt={1} color="gray.400" fontSize="xs">همه تنظیمات اصلی در یک صفحه؛ گزینه‌های کم‌استفاده بسته‌اند.</Text></Box>
        </DrawerHeader>

        <DrawerBody px={{ base: 4, md: 5 }} py={4} overflowY="auto">
          {capabilitiesQuery.isLoading ? <Skeleton h="240px" borderRadius="12px" /> : capabilitiesQuery.isError ? <Alert status="error"><AlertIcon />مجوزهای حساب بارگذاری نشد.</Alert> : (
            <Stack spacing={3}>
              <Section title="مشخصات" description="شماره تلفن اختیاری است؛ در صورت ورود باید ۱۱ رقم و با 09 شروع شود.">
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                  <FormControl isRequired><FormLabel>{t("admins.username")}</FormLabel><Input ref={usernameRef} value={form.username} isDisabled={isEditing} maxLength={34} dir="ltr" autoComplete="username" onChange={(e) => setField("username", e.target.value)} /></FormControl>
                  <FormControl isRequired={!isEditing}><FormLabel>{t("admins.password")}</FormLabel><Input type="password" value={form.password || ""} dir="ltr" autoComplete="new-password" placeholder={isEditing ? t("admins.passwordKeep") : ""} onChange={(e) => setField("password", e.target.value)} /></FormControl>
                  <FormControl><FormLabel>شماره تلفن</FormLabel><Input type="tel" inputMode="numeric" autoComplete="tel" maxLength={11} placeholder="09xxxxxxxxx" value={form.phone || ""} onChange={(e) => setField("phone", e.target.value)} dir="ltr" /></FormControl>
                  <FormControl><FormLabel>{t("admins.role")}</FormLabel><Select value={form.role} isDisabled={isEditing} onChange={(e) => setField("role", e.target.value as ManagedAdminPayload["role"])}>{allowedRoles.map((role) => <option key={role} value={role}>{t(`admins.role.${role}`)}</option>)}</Select><FormHelperText>نقش فرزند نمی‌تواند از والد بالاتر باشد.</FormHelperText></FormControl>
                </SimpleGrid>
              </Section>

              <Section title="نوع حساب" description={isEditing ? "نوع حساب بعد از ساخت ثابت می‌ماند." : "انتخاب اجباری است و هیچ گزینه‌ای از قبل انتخاب نشده است."}>
                {isEditing ? <HStack><Badge colorScheme="primary">{billingLabels[mode].title}</Badge><Text color="gray.400" fontSize="xs">{billingLabels[mode].help}</Text></HStack> : (
                  <SimpleGrid columns={{ base: 1, md: Math.min(Math.max(allowedModes.length, 1), 3) }} gap={2}>
                    {allowedModes.filter((item) => item !== "LEGACY_COMPAT" && item !== "SEAT_CREDIT").map((item) => (
                      <Button key={item} type="button" minH="76px" h="auto" py={3} px={3} whiteSpace="normal" textAlign="start" justifyContent="flex-start" variant={billingMode === item ? "solid" : "outline"} colorScheme={billingMode === item ? "green" : "gray"} onClick={() => selectBillingMode(item)}>
                        <Box><Text fontWeight="800">{billingLabels[item].title}</Text><Text mt={1} fontSize="xs" fontWeight="400" opacity={0.78}>{billingLabels[item].help}</Text></Box>
                      </Button>
                    ))}
                  </SimpleGrid>
                )}
                {!isEditing && billingMode && (
                  <FormControl mt={3} isRequired={billingMode === "USER_CREDIT"} maxW="360px">
                    <FormLabel>{billingMode === "USER_CREDIT" ? "تعداد اکانت قابل ساخت" : "اعتبار قابل استفاده (گیگابایت)"}</FormLabel>
                    <Input type="number" min={billingMode === "USER_CREDIT" ? 1 : 0.01} step={billingMode === "USER_CREDIT" ? 1 : 0.01} dir="ltr" value={billingMode === "USER_CREDIT" ? form.policy.max_users ?? "" : form.policy.total_traffic === null ? "" : form.policy.total_traffic / GIB} onChange={(e) => billingMode === "USER_CREDIT" ? setPolicy("max_users", nullableNumber(e)) : setPolicy("total_traffic", e.target.value === "" ? null : Math.round(Number(e.target.value) * GIB))} />
                    <FormHelperText>{billingMode === "USER_CREDIT" ? "هر اکانت یک واحد کم می‌کند؛ تعداد دستگاه اثری ندارد." : "خالی فقط وقتی مجاز است که والد اعتبار نامحدود داشته باشد."}</FormHelperText>
                  </FormControl>
                )}
              </Section>

              <Section title="اجازه ساخت ادمین" description={`سهم باقی‌مانده شما: ${capabilitiesQuery.data?.admin_creation_remaining ?? "نامحدود"}`}>
                <Stack spacing={3}>
                  <HStack justify="space-between" minH="44px"><Box><Text fontSize="sm" fontWeight="700">اجازه ساخت زیرادمین</Text><Text color="gray.400" fontSize="xs">ساخت هر ادمین یک واحد از بودجه کم می‌کند.</Text></Box><Switch colorScheme="primary" isChecked={form.can_create_admins} isDisabled={!capabilitiesQuery.data?.can_delegate_admin_creation} onChange={(e) => setForm((current) => ({ ...current, can_create_admins: e.target.checked, can_delegate_admin_creation: e.target.checked ? current.can_delegate_admin_creation : false, admin_creation_limit: e.target.checked ? current.admin_creation_limit : 0 }))} /></HStack>
                  {form.can_create_admins && <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                    <FormControl><FormLabel>تعداد ادمین قابل ساخت</FormLabel><Input type="number" min={0} dir="ltr" value={form.admin_creation_limit ?? ""} onChange={(e) => setField("admin_creation_limit", nullableNumber(e))} /><FormHelperText>خالی یعنی نامحدود و فقط برای والد نامحدود مجاز است.</FormHelperText></FormControl>
                    <HStack justify="space-between" align="start" p={3} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px"><Box><Text fontSize="sm" fontWeight="700">اجازه واگذاری این دسترسی</Text><Text color="gray.400" fontSize="xs" mt={1}>این ادمین بتواند به فرزند خودش نیز اجازه ساخت بدهد.</Text></Box><Switch colorScheme="primary" isChecked={form.can_delegate_admin_creation} isDisabled={!capabilitiesQuery.data?.can_delegate_admin_creation} onChange={(e) => setField("can_delegate_admin_creation", e.target.checked)} /></HStack>
                  </SimpleGrid>}
                  {mode === "USED_TRAFFIC" && capabilitiesQuery.data?.can_create_allocated_children && form.can_create_admins && <HStack justify="space-between" minH="44px" p={3} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px"><Box><Text fontSize="sm" fontWeight="700">اجازه ساخت فرزند «حجم ساخته‌شده»</Text><Text color="gray.400" fontSize="xs">فرزند هنگام ساخت باید بین مصرف واقعی و حجم ساخته‌شده انتخاب کند.</Text></Box><Switch colorScheme="primary" isChecked={form.can_create_allocated_children} onChange={(e) => setField("can_create_allocated_children", e.target.checked)} /></HStack>}
                </Stack>
              </Section>

              <Section title="روش ساخت کاربر" description="حالت امن، ساخت فقط از پلن است. ساخت سفارشی باید جداگانه توسط والد مجاز شود.">
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={2}>
                  {(capabilitiesQuery.data?.allowed_child_user_creation_modes || ["PLAN_ONLY"]).map((creationMode) => (
                    <Button key={creationMode} type="button" aria-pressed={form.user_creation_mode === creationMode} minH="58px" h="auto" py={2.5} whiteSpace="normal" textAlign="start" justifyContent="flex-start" variant={form.user_creation_mode === creationMode ? "solid" : "outline"} colorScheme={form.user_creation_mode === creationMode ? "green" : "gray"} onClick={() => setField("user_creation_mode", creationMode)}>
                      <Box><Text fontWeight="800">{creationMode === "PLAN_ONLY" ? "فقط ساخت از پلن" : "ساخت سفارشی"}</Text><Text mt={1} fontSize="xs" fontWeight="400" opacity={0.78}>{creationMode === "PLAN_ONLY" ? "حجم، مدت، دستگاه و پروتکل از پلن می‌آیند." : "ادمین می‌تواند مشخصات کاربر را در محدوده واگذارشده تعیین کند."}</Text></Box>
                    </Button>
                  ))}
                </SimpleGrid>
                <HStack mt={3} justify="space-between" minH="44px" p={3} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px">
                  <Box><Text fontSize="sm" fontWeight="700">اجازه مدیریت پلن</Text><Text color="gray.400" fontSize="xs">ساخت و ویرایش پلن فقط با مجوز جداگانه والد.</Text></Box>
                  <Switch isChecked={form.can_manage_plans} isDisabled={!capabilitiesQuery.data?.can_delegate_plan_management} onChange={(e) => setField("can_manage_plans", e.target.checked)} />
                </HStack>
              </Section>

              {isEditing && admin?.parent_admin_id !== null && mode !== "LEGACY_COMPAT" && (
                <Section title="تغییر سریع اعتبار" description={`اعتبار فعلی: ${displayedBalance}`}>
                  <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2}>
                    <FormControl maxW={{ md: "180px" }}><FormLabel>مقدار ({accountUnit})</FormLabel><Input type="number" min={1} step={["USER_CREDIT", "SEAT_CREDIT"].includes(mode) ? 1 : 0.01} dir="ltr" value={creditAmount} onChange={(e) => setCreditAmount(e.target.value)} /></FormControl>
                    <FormControl flex="1"><FormLabel>یادداشت اختیاری</FormLabel><Input maxLength={512} value={creditReason} onChange={(e) => setCreditReason(e.target.value)} /></FormControl>
                    <Button type="button" colorScheme="primary" isDisabled={!creditAmountValid} isLoading={creditMutation.isLoading} onClick={() => adjustCredit("grant")}>افزایش</Button>
                    <Button type="button" variant="outline" colorScheme="orange" isDisabled={!creditAmountValid} isLoading={creditMutation.isLoading} onClick={() => adjustCredit("reclaim")}>کاهش</Button>
                  </Stack>
                </Section>
              )}

              <Accordion allowMultiple reduceMotion>
                <AccordionItem borderColor="var(--panel-border)"><AccordionButton minH="48px"><Box flex="1" textAlign="start"><Text fontWeight="800">محدودیت‌های اختیاری</Text><Text fontSize="xs" color="gray.400">تاریخ پایان، بیشترین مدت و سقف کاربران</Text></Box><AccordionIcon /></AccordionButton><AccordionPanel px={0} pb={3}><Section title="محدودیت‌ها"><SimpleGrid columns={{ base: 1, md: 3 }} gap={3}>
                  {mode !== "USER_CREDIT" && <FormControl><FormLabel>بیشترین تعداد کاربر</FormLabel><Input type="number" min={1} dir="ltr" value={form.policy.max_users ?? ""} onChange={(e) => setPolicy("max_users", nullableNumber(e))} /></FormControl>}
                  <FormControl><FormLabel>بیشترین مدت اشتراک (روز)</FormLabel><Input type="number" min={1} dir="ltr" value={form.policy.max_user_duration_days ?? ""} onChange={(e) => setPolicy("max_user_duration_days", nullableNumber(e))} /></FormControl>
                  <FormControl><FormLabel>تاریخ پایان ادمین</FormLabel><Input type="date" dir="ltr" value={form.policy.expiry_date || ""} onChange={(e) => setPolicy("expiry_date", e.target.value || null)} /></FormControl>
                </SimpleGrid></Section></AccordionPanel></AccordionItem>

                <AccordionItem borderColor="var(--panel-border)"><AccordionButton minH="48px"><Box flex="1" textAlign="start"><Text fontWeight="800">پلن‌ها و محدوده دسترسی</Text><Text fontSize="xs" color="gray.400">فقط برای محدودکردن ورودی، دستگاه یا دسته پلن باز کنید.</Text></Box><AccordionIcon /></AccordionButton><AccordionPanel px={0} pb={3}><Stack spacing={3}>
                  <Section title="دسته‌های پلن">{categoriesQuery.isLoading ? <Skeleton h="48px" /> : categoriesQuery.isError ? <Alert status="error"><AlertIcon />بارگذاری نشد</Alert> : <Flex gap={2} wrap="wrap">{(categoriesQuery.data || []).map((category) => <Checkbox key={category.id} px={2} minH="40px" isChecked={form.plan_category_ids.includes(category.id)} onChange={(e) => togglePlanCategory(category.id, e.target.checked)}>{category.name}</Checkbox>)}</Flex>}</Section>
                  <SimpleGrid columns={{ base: 1, lg: 2 }} gap={3}>
                    <Section title="ورودی‌های مجاز"><Checkbox isChecked={form.policy.all_inbounds} onChange={(e) => setPolicy("all_inbounds", e.target.checked)}>همه ورودی‌ها</Checkbox>{!form.policy.all_inbounds && <Stack mt={3}><Input value={inboundSearch} onChange={(e) => setInboundSearch(e.target.value)} placeholder="جست‌وجوی ورودی" /><Stack maxH="180px" overflowY="auto">{availableInbounds.map((item) => <Checkbox key={item.tag} minH="40px" isChecked={form.policy.allowed_inbounds.includes(item.tag)} onChange={(e) => toggleInbound(item.tag, e.target.checked)}><Text dir="ltr">{item.tag}</Text></Checkbox>)}</Stack></Stack>}</Section>
                    <Section title="تعداد دستگاه قابل انتخاب"><Checkbox isChecked={form.policy.all_user_limits} onChange={(e) => setPolicy("all_user_limits", e.target.checked)}>بدون محدودیت انتخاب</Checkbox>{!form.policy.all_user_limits && <Stack mt={3}><HStack><Input type="number" min={1} dir="ltr" value={newUserLimit} onChange={(e) => setNewUserLimit(e.target.value)} /><Button type="button" onClick={addUserLimit}>افزودن</Button></HStack><Flex gap={2} wrap="wrap">{form.policy.allowed_user_limits.map((limit) => <Tag key={limit}><TagLabel>{limit}</TagLabel><TagCloseButton onClick={() => setPolicy("allowed_user_limits", form.policy.allowed_user_limits.filter((value) => value !== limit))} /></Tag>)}</Flex></Stack>}</Section>
                  </SimpleGrid>
                  <Section title="نوع اشتراک‌های مجاز"><SimpleGrid columns={{ base: 1, md: 2 }} gap={2}>{subscriptionModes.map((item) => <Checkbox key={item} minH="42px" isChecked={form.policy.allowed_subscription_modes.includes(item)} onChange={(e) => toggleSubscriptionMode(item, e.target.checked)}>{t(`admins.subscriptionMode.${item}`)}</Checkbox>)}</SimpleGrid></Section>
                </Stack></AccordionPanel></AccordionItem>

                <AccordionItem borderColor="var(--panel-border)"><AccordionButton minH="48px"><Box flex="1" textAlign="start"><Text fontWeight="800">گزینه‌های پیشرفته</Text><Text fontSize="xs" color="gray.400">تلگرام، حریم خصوصی و محدودکردن عملیات کاربر</Text></Box><AccordionIcon /></AccordionButton><AccordionPanel px={0} pb={3}><Section title="پیشرفته" description="این محدودیت‌ها در همه نوع‌های اعتبار مستقل از حسابداری اعمال می‌شوند."><SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                  <FormControl><FormLabel>{t("admins.telegramId")}</FormLabel><Input type="number" value={form.telegram_id ?? ""} dir="ltr" onChange={(e) => setField("telegram_id", nullableNumber(e))} /></FormControl>
                  <HStack justify="space-between" p={3} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px"><Text fontSize="sm">نمایش کامل IP کاربر</Text><Switch isChecked={form.policy.view_full_client_ip} onChange={(e) => setPolicy("view_full_client_ip", e.target.checked)} /></HStack>
                  {advancedPolicyOptions.map((item) => <HStack key={item.key} justify="space-between" align="start" p={3} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px"><Box pe={2}><Text fontSize="sm">{t(item.label)}</Text><Text mt={1} fontSize="xs" color="gray.400">{t(item.help)}</Text></Box><Switch flexShrink={0} isChecked={Boolean(form.policy[item.key])} onChange={(e) => setPolicy(item.key, e.target.checked as never)} /></HStack>)}
                </SimpleGrid></Section></AccordionPanel></AccordionItem>
              </Accordion>
            </Stack>
          )}
        </DrawerBody>

        <DrawerFooter gap={2} px={{ base: 4, md: 5 }} py={3} borderTopWidth="1px" borderColor="var(--panel-border)" bg="var(--panel-surface)">
          <Button type="button" variant="ghost" onClick={onClose}>{t("cancel")}</Button><Box flex={1} /><Button type="submit" colorScheme="primary" isLoading={mutation.isLoading} isDisabled={capabilitiesQuery.isLoading || capabilitiesQuery.isError}>{t("save")}</Button>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};
