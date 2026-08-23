import {
  Accordion,
  AccordionButton,
  AccordionIcon,
  AccordionItem,
  AccordionPanel,
  Alert,
  AlertIcon,
  Box,
  Button,
  Checkbox,
  Divider,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  Input,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Tag,
  TagCloseButton,
  TagLabel,
  Text,
  useToast,
} from "@chakra-ui/react";
import { useDashboard } from "contexts/DashboardContext";
import { ChangeEvent, FC, FormEvent, ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import {
  AdminPolicy,
  ManagedAdmin,
  ManagedAdminPayload,
  PlanCategory,
  SubscriptionMode,
} from "types/Admin";
import { localizedApiError } from "utils/apiError";
import { formatBytes } from "utils/formatByte";

const GIB = 1024 ** 3;

const emptyPolicy = (): AdminPolicy => ({
  billing_mode: "LEGACY_COMPAT",
  total_traffic: null,
  expiry_date: null,
  user_limit: null,
  max_users: null,
  device_capacity_limit: null,
  admin_traffic_warning_percent: 80,
  sudo_traffic_warning_percent: 80,
  all_inbounds: true,
  allowed_inbounds: [],
  all_user_limits: true,
  allowed_user_limits: [],
  allowed_subscription_modes: [
    "limited_traffic_unlimited_devices",
    "unlimited_traffic_limited_devices",
    "limited_traffic_limited_devices",
  ],
  view_full_client_ip: false,
  max_user_duration_days: null,
  calculate_volume: "used_traffic",
  prevent_user_creation: false,
  prevent_user_deletion: false,
  prevent_user_reset: false,
  prevent_revoke_subscription: false,
  prevent_unlimited_traffic: false,
});

const emptyAdmin = (): ManagedAdminPayload => ({
  username: "",
  password: "",
  is_sudo: false,
  role: "ADMIN",
  telegram_id: null,
  phone: "",
  discord_webhook: null,
  policy: emptyPolicy(),
  plan_category_ids: [],
});

const steps = [
  { title: "مشخصات ادمین", description: "نام کاربری و راه تماس" },
  { title: "نوع اعتبار", description: "روش کم‌شدن اعتبار" },
  { title: "محدودیت‌ها", description: "تعداد کاربر و زمان" },
  { title: "دسترسی‌ها", description: "پلن‌ها و ورودی‌ها" },
  { title: "تنظیمات بیشتر", description: "گزینه‌های کم‌استفاده" },
];

const Section: FC<{ title: string; description: string; children: ReactNode }> = ({
  title,
  description,
  children,
}) => (
  <Box
    p={{ base: 4, md: 5 }}
    bg="#0d1812"
    borderWidth="1px"
    borderColor="#33483b"
    borderRadius="14px"
  >
    <Text as="h3" fontWeight="800" fontSize="md">{title}</Text>
    <Text color="gray.400" fontSize="sm" mt={1}>{description}</Text>
    <Box mt={5}>{children}</Box>
  </Box>
);

type Props = {
  isOpen: boolean;
  admin: ManagedAdmin | null;
  onClose: () => void;
};

export const AdminFormDrawer: FC<Props> = ({ isOpen, admin, onClose }) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { inbounds } = useDashboard();
  const usernameRef = useRef<HTMLInputElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [form, setForm] = useState<ManagedAdminPayload>(emptyAdmin());
  const [step, setStep] = useState(0);
  const [inboundSearch, setInboundSearch] = useState("");
  const [newUserLimit, setNewUserLimit] = useState("");
  const [creditAmount, setCreditAmount] = useState("");
  const [creditReason, setCreditReason] = useState("");
  const [creditBalance, setCreditBalance] = useState<number | null>(null);
  const isEditing = Boolean(admin);

  useEffect(() => {
    setForm(admin ? {
      username: admin.username,
      password: "",
      is_sudo: admin.is_sudo,
      role: admin.role,
      telegram_id: admin.telegram_id,
      phone: admin.phone,
      discord_webhook: admin.discord_webhook,
      policy: { ...admin.policy },
      plan_category_ids: [...admin.plan_category_ids],
    } : emptyAdmin());
    setStep(0);
    setInboundSearch("");
    setNewUserLimit("");
    setCreditAmount("");
    setCreditReason("");
    setCreditBalance(admin?.quota.credit_remaining ?? null);
  }, [admin, isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, behavior: "auto" });
  }, [step]);

  const availableInbounds = useMemo(
    () => [...inbounds.values()]
      .flat()
      .filter((inbound) => inbound.tag.toLocaleLowerCase().includes(inboundSearch.trim().toLocaleLowerCase())),
    [inbounds, inboundSearch]
  );

  const categoriesQuery = useQuery<PlanCategory[], Error>(
    "plan-categories",
    () => fetch("/plan-categories"),
    { enabled: isOpen, staleTime: 30000 }
  );

  const mutation = useMutation(
    (payload: ManagedAdminPayload) => fetch(
      isEditing ? `/admin-management/${admin?.username}` : "/admin-management",
      { method: isEditing ? "PUT" : "POST", body: payload }
    ),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("admin-capabilities");
        toast({ title: t(isEditing ? "admins.updated" : "admins.created"), status: "success", duration: 3000 });
        onClose();
      },
      onError: (error) => {
        toast({
          title: t("admins.saveFailed"),
          description: localizedApiError(error),
          status: "error",
          duration: 5000,
        });
      },
    }
  );

  const creditRequestId = useMemo(
    () => crypto.randomUUID(),
    [admin?.id, creditAmount, creditReason]
  );
  const creditMutation = useMutation<
    { balance_after: number | null },
    Error,
    { operation: "grant" | "reclaim"; amount: number }
  >(
    ({ operation, amount }) => fetch(
      `/admin-management/${encodeURIComponent(admin?.username || "")}/credit/${operation}`,
      {
        method: "POST",
        body: {
          amount,
          idempotency_key: `admin-form-${operation}-${creditRequestId}`,
          note: creditReason.trim(),
        },
      }
    ),
    {
      onSuccess: (result, variables) => {
        setCreditBalance(result.balance_after);
        setCreditAmount("");
        setCreditReason("");
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("admin-hierarchy-tree");
        queryClient.invalidateQueries("account-summary");
        toast({
          title: variables.operation === "grant" ? "اعتبار اضافه شد" : "اعتبار کم شد",
          status: "success",
          duration: 3000,
        });
      },
      onError: (error) => {
        toast({
          title: "تغییر اعتبار انجام نشد",
          description: localizedApiError(error),
          status: "error",
          duration: 5000,
        });
      },
    }
  );

  const setField = <K extends keyof ManagedAdminPayload>(key: K, value: ManagedAdminPayload[K]) =>
    setForm((current) => ({ ...current, [key]: value }));
  const setPolicy = <K extends keyof AdminPolicy>(key: K, value: AdminPolicy[K]) =>
    setForm((current) => ({ ...current, policy: { ...current.policy, [key]: value } }));
  const nullableNumber = (event: ChangeEvent<HTMLInputElement>) =>
    event.target.value === "" ? null : Number(event.target.value);

  const showWarning = (title: string) => {
    toast({ title, status: "warning", duration: 3000 });
    return false;
  };

  const validateStep = (targetStep = step) => {
    if (targetStep === 0) {
      if (!form.username.trim()) return showWarning("نام کاربری را وارد کنید");
      if (!isEditing && !form.password) return showWarning(t("admins.passwordRequired"));
      if (!form.phone?.trim()) return showWarning("شماره تماس را وارد کنید");
    }
    if (targetStep === 3) {
      if (!form.policy.all_inbounds && form.policy.allowed_inbounds.length === 0) {
        return showWarning(t("admins.selectInboundRequired"));
      }
      if (!form.policy.all_user_limits && form.policy.allowed_user_limits.length === 0) {
        return showWarning(t("admins.selectUserLimitRequired"));
      }
      if (form.policy.allowed_subscription_modes.length === 0) {
        return showWarning(t("admins.selectSubscriptionModeRequired"));
      }
    }
    return true;
  };

  const goToStep = (nextStep: number) => {
    if (nextStep > step && !validateStep(step)) return;
    setStep(nextStep);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (![0, 3].every(validateStep)) return;
    const payload = { ...form };
    if (isEditing && !payload.password) delete payload.password;
    mutation.mutate(payload);
  };

  const toggleInbound = (tag: string, checked: boolean) => setPolicy(
    "allowed_inbounds",
    (checked
      ? [...new Set([...form.policy.allowed_inbounds, tag])]
      : form.policy.allowed_inbounds.filter((value) => value !== tag)
    ).sort()
  );

  const addUserLimit = () => {
    const value = Number(newUserLimit);
    if (!Number.isInteger(value) || value < 1) return;
    setPolicy("allowed_user_limits", [...new Set([...form.policy.allowed_user_limits, value])].sort((a, b) => a - b));
    setNewUserLimit("");
  };

  const seatCredit = form.policy.billing_mode === "SEAT_CREDIT";
  const parsedCreditAmount = Number(creditAmount);
  const creditAmountIsValid = Number.isFinite(parsedCreditAmount)
    && parsedCreditAmount > 0
    && (!seatCredit || Number.isInteger(parsedCreditAmount));
  const currentCredit = creditBalance === null
    ? "نامحدود"
    : seatCredit
      ? `${creditBalance} دستگاه`
      : String(formatBytes(creditBalance));
  const adjustCredit = (operation: "grant" | "reclaim") => {
    if (!admin || !creditAmountIsValid || !creditReason.trim()) return;
    if (operation === "reclaim" && !window.confirm(`اعتبار ${admin.username} کم شود؟`)) return;
    creditMutation.mutate({
      operation,
      amount: seatCredit ? parsedCreditAmount : Math.round(parsedCreditAmount * GIB),
    });
  };

  const toggleSubscriptionMode = (mode: SubscriptionMode, checked: boolean) => setPolicy(
    "allowed_subscription_modes",
    checked
      ? [...new Set([...form.policy.allowed_subscription_modes, mode])]
      : form.policy.allowed_subscription_modes.filter((value) => value !== mode)
  );

  const togglePlanCategory = (categoryId: number, checked: boolean) => setField(
    "plan_category_ids",
    checked
      ? [...new Set([...form.plan_category_ids, categoryId])]
      : form.plan_category_ids.filter((value) => value !== categoryId)
  );

  const operationToggles: Array<[keyof AdminPolicy, string, string]> = [
    ["prevent_user_creation", "admins.preventCreate", "admins.preventCreateHelp"],
    ["prevent_user_deletion", "admins.preventDelete", "admins.preventDeleteHelp"],
    ["prevent_user_reset", "admins.preventReset", "admins.preventResetHelp"],
    ["prevent_revoke_subscription", "admins.preventRevoke", "admins.preventRevokeHelp"],
    ["prevent_unlimited_traffic", "admins.preventUnlimited", "admins.preventUnlimitedHelp"],
  ];
  const subscriptionModes: SubscriptionMode[] = [
    "limited_traffic_unlimited_devices",
    "unlimited_traffic_limited_devices",
    "limited_traffic_limited_devices",
    "unlimited_traffic_unlimited_devices",
  ];

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      placement={i18n.dir() === "rtl" ? "right" : "left"}
      size="full"
      initialFocusRef={usernameRef}
    >
      <DrawerOverlay bg="rgba(0, 0, 0, .72)" backdropFilter="blur(4px)" />
      <DrawerContent
        as="form"
        onSubmit={submit}
        dir={i18n.dir()}
        ms="auto"
        w="full"
        maxW={{ base: "100vw", md: "860px" }}
        h="100dvh"
        maxH="100dvh"
        overflow="hidden"
        bg="#111d17"
        color="gray.100"
        borderInlineStartWidth={{ md: "1px" }}
        borderColor="#33483b"
      >
        <DrawerHeader flex="0 0 auto" px={{ base: 4, md: 6 }} py={4} borderBottomWidth="1px" borderColor="#33483b">
          <DrawerCloseButton top={4} insetInlineEnd={4} />
          <Box pe={12}>
            <Text fontSize="lg" fontWeight="800">{t(isEditing ? "admins.editTitle" : "admins.createTitle")}</Text>
            <Text mt={1} color="gray.400" fontSize="sm">مرحله {step + 1} از {steps.length} · {steps[step].description}</Text>
          </Box>
          <Flex mt={4} gap={2} overflowX="auto" pb={1} css={{ scrollbarWidth: "thin" }}>
            {steps.map((item, index) => (
              <Button
                key={item.title}
                type="button"
                minW={{ base: "134px", md: 0 }}
                flex={{ md: 1 }}
                minH="44px"
                h="auto"
                py={2}
                px={3}
                justifyContent="flex-start"
                variant={index === step ? "solid" : "ghost"}
                colorScheme={index === step ? "primary" : "gray"}
                color={index === step ? "#07130e" : "gray.300"}
                borderWidth="1px"
                borderColor={index === step ? "primary.400" : "whiteAlpha.200"}
                onClick={() => goToStep(index)}
              >
                <HStack spacing={2} minW={0}>
                  <Flex
                    flex="0 0 auto"
                    align="center"
                    justify="center"
                    w="22px"
                    h="22px"
                    borderRadius="full"
                    bg={index === step ? "blackAlpha.200" : index < step ? "primary.500" : "whiteAlpha.100"}
                    color={index < step ? "#07130e" : "inherit"}
                    fontSize="xs"
                  >{index + 1}</Flex>
                  <Text fontSize="xs" fontWeight="750" noOfLines={1}>{item.title}</Text>
                </HStack>
              </Button>
            ))}
          </Flex>
        </DrawerHeader>

        <DrawerBody
          ref={scrollRef}
          flex="1 1 auto"
          minH={0}
          overflowY="auto"
          overscrollBehavior="contain"
          px={{ base: 4, md: 6 }}
          py={5}
          scrollPaddingBottom="24px"
        >
          {step === 0 && (
            <Section title="مشخصات ادمین" description="نام کاربری، رمز و شماره تماس را وارد کنید.">
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={5}>
                <FormControl isRequired>
                  <FormLabel>{t("admins.username")}</FormLabel>
                  <Input ref={usernameRef} value={form.username} disabled={isEditing} maxLength={34} dir="ltr" autoComplete="username" onChange={(e) => setField("username", e.target.value)} />
                </FormControl>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>{t("admins.password")}</FormLabel>
                  <Input type="password" value={form.password || ""} dir="ltr" autoComplete="new-password" placeholder={isEditing ? t("admins.passwordKeep") : ""} onChange={(e) => setField("password", e.target.value)} />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel>شماره تماس</FormLabel>
                  <Input type="tel" autoComplete="tel" maxLength={32} value={form.phone || ""} onChange={(e) => setField("phone", e.target.value)} dir="ltr" />
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.role")}</FormLabel>
                  <Select value={form.role} isDisabled={isEditing} onChange={(event) => setField("role", event.target.value as ManagedAdminPayload["role"])}>
                    <option value="ADMIN">{t("admins.role.ADMIN")}</option>
                    <option value="SUPER_ADMIN">{t("admins.role.SUPER_ADMIN")}</option>
                  </Select>
                  <FormHelperText>{t("admins.roleHelp")}</FormHelperText>
                </FormControl>
              </SimpleGrid>
            </Section>
          )}

          {step === 1 && (
            <Stack spacing={4}>
            <Section title="نوع اعتبار" description="مشخص کنید اعتبار این ادمین چطور کم شود.">
              <Stack spacing={5}>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>نوع اعتبار</FormLabel>
                  <Select value={form.policy.billing_mode} isDisabled={isEditing} onChange={(event) => setPolicy("billing_mode", event.target.value as AdminPolicy["billing_mode"])}>
                    <option value="LEGACY_COMPAT">حالت قدیمی</option>
                    <option value="SEAT_CREDIT">اعتبار دستگاه</option>
                    <option value="USED_TRAFFIC">کم‌شدن با مصرف واقعی</option>
                    <option value="ALLOCATED_TRAFFIC">کم‌شدن با حجم اختصاص‌داده‌شده</option>
                  </Select>
                  <FormHelperText>بعد از ساخت ادمین، نوع اعتبار قابل تغییر نیست.</FormHelperText>
                </FormControl>
                {form.policy.billing_mode === "SEAT_CREDIT" ? (
                  <FormControl isReadOnly={isEditing} isRequired={!isEditing}>
                    <FormLabel>{t("admins.deviceCapacity")}</FormLabel>
                    <Input type="number" min={1} dir="ltr" value={form.policy.device_capacity_limit ?? ""} readOnly={isEditing} onChange={(e) => setPolicy("device_capacity_limit", nullableNumber(e))} />
                    <FormHelperText>تعداد اعتبار دستگاه اولیه را وارد کنید.</FormHelperText>
                  </FormControl>
                ) : (
                  <FormControl isReadOnly={isEditing}>
                    <FormLabel>{t("admins.creditLimit")}</FormLabel>
                    <Input type="number" min={0} step="0.01" dir="ltr" value={form.policy.total_traffic === null ? "" : form.policy.total_traffic / GIB} readOnly={isEditing} onChange={(event) => setPolicy("total_traffic", event.target.value === "" ? null : Math.round(Number(event.target.value) * GIB))} />
                    <FormHelperText>{t(isEditing ? "admins.creditLedgerHelp" : "admins.initialCreditLedgerHelp")}</FormHelperText>
                  </FormControl>
                )}
                {form.policy.billing_mode === "LEGACY_COMPAT" && (
                  <FormControl>
                    <FormLabel>{t("admins.volumeMode")}</FormLabel>
                    <Select value={form.policy.calculate_volume} onChange={(event) => setPolicy("calculate_volume", event.target.value as AdminPolicy["calculate_volume"])}>
                      <option value="used_traffic">{t("admins.usedTrafficMode")}</option>
                      <option value="created_traffic">{t("admins.createdTrafficMode")}</option>
                    </Select>
                    <FormHelperText>{t("admins.volumeModeHelp")}</FormHelperText>
                  </FormControl>
                )}
              </Stack>
            </Section>
            {isEditing && admin?.parent_admin_id !== null && (
              <Section title="افزایش یا کاهش اعتبار" description="این تغییر همان لحظه ثبت می‌شود و به دکمه ذخیره فرم وابسته نیست.">
                <Stack spacing={4}>
                  <Box p={4} bg="whiteAlpha.50" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="10px">
                    <Text color="gray.400" fontSize="xs">اعتبار فعلی</Text>
                    <Text mt={1} fontSize="xl" fontWeight="800" sx={{ fontVariantNumeric: "tabular-nums" }}>{currentCredit}</Text>
                  </Box>
                  <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
                    <FormControl isRequired>
                      <FormLabel>مقدار ({seatCredit ? "دستگاه" : "گیگابایت"})</FormLabel>
                      <Input
                        type="number"
                        min={seatCredit ? 1 : 0.01}
                        step={seatCredit ? 1 : 0.01}
                        dir="ltr"
                        value={creditAmount}
                        onChange={(event) => setCreditAmount(event.target.value)}
                      />
                    </FormControl>
                    <FormControl isRequired>
                      <FormLabel>دلیل تغییر</FormLabel>
                      <Input
                        maxLength={512}
                        value={creditReason}
                        onChange={(event) => setCreditReason(event.target.value)}
                      />
                    </FormControl>
                  </SimpleGrid>
                  <HStack justify="end" flexWrap="wrap">
                    <Button
                      type="button"
                      minH="44px"
                      colorScheme="green"
                      isLoading={creditMutation.isLoading}
                      isDisabled={!creditAmountIsValid || !creditReason.trim()}
                      onClick={() => adjustCredit("grant")}
                    >
                      اضافه‌کردن اعتبار
                    </Button>
                    <Button
                      type="button"
                      minH="44px"
                      variant="outline"
                      colorScheme="orange"
                      isLoading={creditMutation.isLoading}
                      isDisabled={!creditAmountIsValid || !creditReason.trim()}
                      onClick={() => adjustCredit("reclaim")}
                    >
                      کم‌کردن اعتبار
                    </Button>
                  </HStack>
                </Stack>
              </Section>
            )}
            </Stack>
          )}

          {step === 2 && (
            <Section title="محدودیت‌ها" description="سقف تعداد کاربر، مدت اشتراک و تاریخ پایان ادمین را تنظیم کنید.">
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={5}>
                <FormControl>
                  <FormLabel>{t("admins.operationLimit")}</FormLabel>
                  <Input type="number" min={0} dir="ltr" value={form.policy.user_limit ?? ""} onChange={(e) => setPolicy("user_limit", nullableNumber(e))} />
                  <FormHelperText>{t("admins.operationLimitHelp")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.maxUsers")}</FormLabel>
                  <Input type="number" min={1} dir="ltr" value={form.policy.max_users ?? ""} onChange={(e) => setPolicy("max_users", nullableNumber(e))} />
                  <FormHelperText>{t("admins.maxUsersHelp")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.maxDuration")}</FormLabel>
                  <Input type="number" min={1} dir="ltr" value={form.policy.max_user_duration_days ?? ""} onChange={(e) => setPolicy("max_user_duration_days", nullableNumber(e))} />
                  <FormHelperText>{t("admins.blankUnlimited")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.expiryDate")}</FormLabel>
                  <Input type="date" dir="ltr" value={form.policy.expiry_date || ""} onChange={(e) => setPolicy("expiry_date", e.target.value || null)} />
                </FormControl>
              </SimpleGrid>
            </Section>
          )}

          {step === 3 && (
            <Stack spacing={4}>
              <Section title={t("admins.planCategories")} description={t("admins.planCategoriesHelp")}>
                {categoriesQuery.isError ? (
                  <Alert status="error"><AlertIcon />{t("admins.planCategoriesLoadFailed")}</Alert>
                ) : categoriesQuery.isLoading ? (
                  <Skeleton h="64px" borderRadius="10px" />
                ) : (categoriesQuery.data || []).length === 0 ? (
                  <Text color="gray.400" fontSize="sm">{t("admins.noPlanCategories")}</Text>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                    {(categoriesQuery.data || []).map((category) => (
                      <Checkbox key={category.id} minH="48px" px={3} colorScheme="primary" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="10px" isChecked={form.plan_category_ids.includes(category.id)} onChange={(event) => togglePlanCategory(category.id, event.target.checked)}>
                        <Text fontSize="sm" fontWeight="650">{category.name}</Text>
                      </Checkbox>
                    ))}
                  </SimpleGrid>
                )}
              </Section>

              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={4}>
                <Section title={t("admins.inboundAccess")} description={t("admins.inboundAccessHelp")}>
                  <Checkbox colorScheme="primary" isChecked={form.policy.all_inbounds} onChange={(event) => setPolicy("all_inbounds", event.target.checked)}>{t("admins.allInbounds")}</Checkbox>
                  {!form.policy.all_inbounds && (
                    <Stack mt={4} spacing={3}>
                      <Input aria-label={t("admins.searchInbounds")} value={inboundSearch} onChange={(event) => setInboundSearch(event.target.value)} placeholder={t("admins.searchInbounds")} />
                      <Stack maxH="210px" overflowY="auto" spacing={1} p={2} borderWidth="1px" borderColor="#33483b" borderRadius="10px">
                        {availableInbounds.map((inbound) => (
                          <Checkbox key={inbound.tag} minH="44px" px={2} colorScheme="primary" isChecked={form.policy.allowed_inbounds.includes(inbound.tag)} onChange={(event) => toggleInbound(inbound.tag, event.target.checked)}>
                            <Text dir="ltr" fontSize="sm" overflowWrap="anywhere">{inbound.tag}</Text>
                          </Checkbox>
                        ))}
                      </Stack>
                    </Stack>
                  )}
                </Section>

                <Section title={t("admins.allowedUserLimits")} description={t("admins.allowedUserLimitsHelp")}>
                  <Checkbox colorScheme="primary" isChecked={form.policy.all_user_limits} onChange={(event) => setPolicy("all_user_limits", event.target.checked)}>{t("admins.allUserLimits")}</Checkbox>
                  {!form.policy.all_user_limits && (
                    <Stack mt={4} spacing={3}>
                      <HStack align="end">
                        <FormControl>
                          <FormLabel>{t("admins.addUserLimit")}</FormLabel>
                          <Input type="number" min={1} step={1} dir="ltr" value={newUserLimit} onChange={(event) => setNewUserLimit(event.target.value)} />
                        </FormControl>
                        <Button type="button" minH="44px" onClick={addUserLimit} isDisabled={!newUserLimit}>{t("add")}</Button>
                      </HStack>
                      <Flex gap={2} wrap="wrap" minH="34px">
                        {form.policy.allowed_user_limits.map((limit) => (
                          <Tag key={limit} colorScheme="yellow" variant="subtle" minH="32px">
                            <TagLabel>{t("admins.userLimitValue", { count: limit })}</TagLabel>
                            <TagCloseButton aria-label={t("remove")} onClick={() => setPolicy("allowed_user_limits", form.policy.allowed_user_limits.filter((value) => value !== limit))} />
                          </Tag>
                        ))}
                      </Flex>
                    </Stack>
                  )}
                </Section>
              </SimpleGrid>

              <Section title={t("admins.subscriptionModes")} description={t("admins.subscriptionModesHelp")}>
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                  {subscriptionModes.map((mode) => (
                    <Checkbox key={mode} minH="52px" px={3} py={2} colorScheme="primary" bg="whiteAlpha.50" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="10px" isChecked={form.policy.allowed_subscription_modes.includes(mode)} onChange={(event) => toggleSubscriptionMode(mode, event.target.checked)}>
                      <Text fontSize="sm" fontWeight="650">{t(`admins.subscriptionMode.${mode}`)}</Text>
                    </Checkbox>
                  ))}
                </SimpleGrid>
              </Section>
            </Stack>
          )}

          {step === 4 && (
            <Section title="تنظیمات بیشتر" description="این گزینه‌ها معمولاً لازم نیستند. هر بخش را فقط در صورت نیاز باز کنید.">
              <Accordion allowMultiple reduceMotion>
                <AccordionItem borderColor="#33483b">
                  <AccordionButton minH="52px" px={1}>
                    <Box flex="1" textAlign="start">
                      <Text fontWeight="750">تلگرام</Text>
                      <Text color="gray.400" fontSize="xs" mt={1}>شناسه تلگرام ادمین، در صورت نیاز</Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel px={1} pb={5}>
                    <FormControl maxW="360px">
                      <FormLabel>{t("admins.telegramId")}</FormLabel>
                      <Input type="number" value={form.telegram_id ?? ""} dir="ltr" onChange={(e) => setField("telegram_id", nullableNumber(e))} />
                    </FormControl>
                  </AccordionPanel>
                </AccordionItem>

                <AccordionItem borderColor="#33483b">
                  <AccordionButton minH="52px" px={1}>
                    <Box flex="1" textAlign="start">
                      <Text fontWeight="750">{t("admins.permissionsSection")}</Text>
                      <Text color="gray.400" fontSize="xs" mt={1}>{t("admins.permissionsSectionHelp")}</Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel px={1} pb={5}>
                    <SimpleGrid columns={{ base: 1, md: 2 }} gap={3}>
                      {operationToggles.map(([key, label, help]) => (
                        <HStack key={key} justify="space-between" align="start" p={4} bg="#111d17" borderWidth="1px" borderColor="#33483b" borderRadius="10px" minW={0}>
                          <Box pe={3} minW={0}>
                            <Text fontSize="sm" fontWeight="650">{t(label)}</Text>
                            <Text fontSize="xs" color="gray.400" mt={1}>{t(help)}</Text>
                          </Box>
                          <Switch flexShrink={0} colorScheme="primary" isChecked={Boolean(form.policy[key])} onChange={(e) => setPolicy(key, e.target.checked as never)} />
                        </HStack>
                      ))}
                    </SimpleGrid>
                  </AccordionPanel>
                </AccordionItem>

                <AccordionItem borderColor="#33483b">
                  <AccordionButton minH="52px" px={1}>
                    <Box flex="1" textAlign="start">
                      <Text fontWeight="750">حریم خصوصی و هشدار مصرف</Text>
                      <Text color="gray.400" fontSize="xs" mt={1}>نمایش کامل IP و زمان نمایش هشدار</Text>
                    </Box>
                    <AccordionIcon />
                  </AccordionButton>
                  <AccordionPanel px={1} pb={5}>
                    <Stack spacing={4}>
                      <HStack justify="space-between" align="start" p={4} bg="#111d17" borderWidth="1px" borderColor="#33483b" borderRadius="10px">
                        <Box pe={3} minW={0}>
                          <Text fontSize="sm" fontWeight="650">{t("admins.viewFullClientIp")}</Text>
                          <Text fontSize="xs" color="gray.400" mt={1}>{t("admins.viewFullClientIpHelp")}</Text>
                        </Box>
                        <Switch flexShrink={0} colorScheme="primary" isChecked={form.policy.view_full_client_ip} onChange={(event) => setPolicy("view_full_client_ip", event.target.checked)} />
                      </HStack>
                      {form.policy.calculate_volume === "used_traffic" && (
                        <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
                          <FormControl isRequired>
                            <FormLabel>{t("admins.adminWarningPercent")}</FormLabel>
                            <Input type="number" min={1} max={100} step={1} dir="ltr" value={form.policy.admin_traffic_warning_percent} onChange={(e) => setPolicy("admin_traffic_warning_percent", Number(e.target.value))} />
                            <FormHelperText>{t("admins.adminWarningPercentHelp")}</FormHelperText>
                          </FormControl>
                          <FormControl isRequired>
                            <FormLabel>{t("admins.sudoWarningPercent")}</FormLabel>
                            <Input type="number" min={1} max={100} step={1} dir="ltr" value={form.policy.sudo_traffic_warning_percent} onChange={(e) => setPolicy("sudo_traffic_warning_percent", Number(e.target.value))} />
                            <FormHelperText>{t("admins.sudoWarningPercentHelp")}</FormHelperText>
                          </FormControl>
                        </SimpleGrid>
                      )}
                    </Stack>
                  </AccordionPanel>
                </AccordionItem>
              </Accordion>
            </Section>
          )}
        </DrawerBody>

        <Divider borderColor="#33483b" />
        <DrawerFooter flex="0 0 auto" gap={3} px={{ base: 4, md: 6 }} py={4} bg="#111d17">
          <Button type="button" minH="44px" variant="ghost" onClick={onClose}>{t("cancel")}</Button>
          <Box flex={1} />
          {step > 0 && <Button type="button" minH="44px" variant="outline" borderColor="#475f50" onClick={() => setStep((value) => value - 1)}>مرحله قبل</Button>}
          {step < steps.length - 1 ? (
            <Button type="button" minH="44px" colorScheme="primary" color="#07130e" onClick={() => goToStep(step + 1)}>ادامه</Button>
          ) : (
            <Button minH="44px" type="submit" colorScheme="primary" color="#07130e" isLoading={mutation.isLoading}>{t("save")}</Button>
          )}
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
};
