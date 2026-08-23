import {
  Alert,
  AlertDialog,
  AlertDialogBody,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  Checkbox,
  Divider,
  Flex,
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Tag,
  TagCloseButton,
  TagLabel,
  Table,
  TableContainer,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  chakra,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import {
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  ShieldCheckIcon,
  TrashIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import { AppShell } from "components/AppShell";
import { AdminHierarchyPanel } from "components/AdminHierarchyPanel";
import { useDashboard } from "contexts/DashboardContext";
import useGetUser from "hooks/useGetUser";
import { ChangeEvent, FC, FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { AdminPolicy, ManagedAdmin, ManagedAdminList, ManagedAdminPayload, PlanCategory, SubscriptionMode } from "types/Admin";
import { formatBytes } from "utils/formatByte";
import { localizedApiError } from "utils/apiError";

const SearchIcon = chakra(MagnifyingGlassIcon, { baseStyle: { w: 4, h: 4 } });
const AddIcon = chakra(PlusIcon, { baseStyle: { w: 4, h: 4 } });
const EditIcon = chakra(PencilSquareIcon, { baseStyle: { w: 4, h: 4 } });
const RemoveIcon = chakra(TrashIcon, { baseStyle: { w: 4, h: 4 } });
const AdminsIcon = chakra(UserGroupIcon, { baseStyle: { w: 5, h: 5 } });
const SudoIcon = chakra(ShieldCheckIcon, { baseStyle: { w: 5, h: 5 } });

const PAGE_SIZE = 20;
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

const getErrorMessage = localizedApiError;

type StatProps = { label: string; value: string | number; icon: JSX.Element };
const AdminStat: FC<StatProps> = ({ label, value, icon }) => (
  <Card variant="outline" p={5} bg="#111d17" color="gray.100" boxShadow="panel" borderRadius="18px" borderColor="#33483b">
    <HStack justify="space-between">
      <Box>
        <Text color="gray.300" fontSize="sm" fontWeight="600">{label}</Text>
        <Text color="white" mt={1} fontSize="2xl" fontWeight="750">{value}</Text>
      </Box>
      <Box color="primary.300" bg="rgba(72, 213, 139, .12)" borderWidth="1px" borderColor="rgba(72, 213, 139, .24)" p={3} borderRadius="12px">
        {icon}
      </Box>
    </HStack>
  </Card>
);

const CreditRemaining: FC<{ admin: ManagedAdmin }> = ({ admin }) => {
  const { t } = useTranslation();
  const quota = admin.quota;
  return (
    <Stack spacing={1} align="start">
      <Text>
        {quota.credit_remaining === null
          ? t("unlimited")
          : admin.policy.billing_mode === "SEAT_CREDIT"
            ? `${quota.credit_remaining} seats`
            : formatBytes(quota.credit_remaining)}
      </Text>
      {quota.credit_usage_percent !== null && (
        <HStack spacing={2}>
          <Text fontSize="xs" color="gray.400">{quota.credit_usage_percent}%</Text>
          {quota.sudo_warning_active && (
            <Badge colorScheme="orange" variant="subtle">{t("admins.creditWarning")}</Badge>
          )}
        </HStack>
      )}
    </Stack>
  );
};

type FormModalProps = {
  isOpen: boolean;
  admin: ManagedAdmin | null;
  onClose: () => void;
};

const AdminFormModal: FC<FormModalProps> = ({ isOpen, admin, onClose }) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { inbounds } = useDashboard();
  const [form, setForm] = useState<ManagedAdminPayload>(emptyAdmin());
  const [inboundSearch, setInboundSearch] = useState("");
  const [newUserLimit, setNewUserLimit] = useState("");
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
  }, [admin, isOpen]);

  const availableInbounds = [...inbounds.values()]
    .flat()
    .filter((inbound) =>
      inbound.tag.toLocaleLowerCase().includes(inboundSearch.trim().toLocaleLowerCase())
    );

  const mutation = useMutation(
    (payload: ManagedAdminPayload) =>
      fetch(isEditing ? `/admin-management/${admin?.username}` : "/admin-management", {
        method: isEditing ? "PUT" : "POST",
        body: payload,
      }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("admin-capabilities");
        toast({ title: t(isEditing ? "admins.updated" : "admins.created"), status: "success", duration: 3000 });
        onClose();
      },
      onError: (error) => {
        toast({ title: t("admins.saveFailed"), description: getErrorMessage(error), status: "error", duration: 5000 });
      },
    }
  );

  const categoriesQuery = useQuery<PlanCategory[], Error>(
    "plan-categories",
    () => fetch("/plan-categories"),
    { enabled: isOpen, staleTime: 30000 }
  );

  const setField = <K extends keyof ManagedAdminPayload>(key: K, value: ManagedAdminPayload[K]) =>
    setForm((current) => ({ ...current, [key]: value }));
  const setPolicy = <K extends keyof AdminPolicy>(key: K, value: AdminPolicy[K]) =>
    setForm((current) => ({ ...current, policy: { ...current.policy, [key]: value } }));
  const nullableNumber = (event: ChangeEvent<HTMLInputElement>) =>
    event.target.value === "" ? null : Number(event.target.value);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!isEditing && !form.password) {
      toast({ title: t("admins.passwordRequired"), status: "warning", duration: 3000 });
      return;
    }
    if (!form.phone?.trim()) {
      toast({ title: "Phone is required for Admin accounts", status: "warning", duration: 3000 });
      return;
    }
    if (!form.policy.all_inbounds && form.policy.allowed_inbounds.length === 0) {
      toast({ title: t("admins.selectInboundRequired"), status: "warning", duration: 3000 });
      return;
    }
    if (!form.policy.all_user_limits && form.policy.allowed_user_limits.length === 0) {
      toast({ title: t("admins.selectUserLimitRequired"), status: "warning", duration: 3000 });
      return;
    }
    if (form.policy.allowed_subscription_modes.length === 0) {
      toast({ title: t("admins.selectSubscriptionModeRequired"), status: "warning", duration: 3000 });
      return;
    }
    const payload = { ...form };
    if (isEditing && !payload.password) delete payload.password;
    mutation.mutate(payload);
  };

  const toggleInbound = (tag: string, checked: boolean) => {
    const next = checked
      ? [...new Set([...form.policy.allowed_inbounds, tag])]
      : form.policy.allowed_inbounds.filter((value) => value !== tag);
    setPolicy("allowed_inbounds", next.sort());
  };

  const addUserLimit = () => {
    const value = Number(newUserLimit);
    if (!Number.isInteger(value) || value < 1) return;
    setPolicy("allowed_user_limits", [...new Set([...form.policy.allowed_user_limits, value])].sort((a, b) => a - b));
    setNewUserLimit("");
  };

  const toggles: Array<[keyof AdminPolicy, string, string]> = [
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

  const toggleSubscriptionMode = (mode: SubscriptionMode, checked: boolean) => {
    setPolicy(
      "allowed_subscription_modes",
      checked
        ? [...new Set([...form.policy.allowed_subscription_modes, mode])]
        : form.policy.allowed_subscription_modes.filter((value) => value !== mode)
    );
  };

  const togglePlanCategory = (categoryId: number, checked: boolean) => {
    setField(
      "plan_category_ids",
      checked
        ? [...new Set([...form.plan_category_ids, categoryId])]
        : form.plan_category_ids.filter((value) => value !== categoryId)
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="5xl" scrollBehavior="inside">
      <ModalOverlay bg="rgba(0, 0, 0, .72)" backdropFilter="blur(4px)" />
      <ModalContent
        as="form"
        onSubmit={submit}
        mx={3}
        maxH="calc(100dvh - 24px)"
        overflow="hidden"
        dir={i18n.dir()}
        bg="#111d17"
        color="gray.100"
        borderWidth="1px"
        borderColor="#33483b"
        borderRadius={{ base: "12px", md: "16px" }}
        boxShadow="elevated"
      >
        <ModalHeader pe={14} lineHeight="1.7">{t(isEditing ? "admins.editTitle" : "admins.createTitle")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody px={{ base: 4, md: 6 }} pb={6} overflowY="auto">
          <Stack spacing={5}>
            <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
              <Text fontWeight="700">{t("admins.accountSection")}</Text>
              <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.accountSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5} mt={4}>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>{t("admins.username")}</FormLabel>
                  <Input value={form.username} disabled={isEditing} maxLength={34} dir="ltr" onChange={(e) => setField("username", e.target.value)} />
                </FormControl>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>{t("admins.password")}</FormLabel>
                  <Input type="password" value={form.password || ""} dir="ltr" placeholder={isEditing ? t("admins.passwordKeep") : ""} onChange={(e) => setField("password", e.target.value)} />
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.telegramId")}</FormLabel>
                  <Input type="number" value={form.telegram_id ?? ""} dir="ltr" onChange={(e) => setField("telegram_id", nullableNumber(e))} />
                </FormControl>
                <FormControl isRequired>
                  <FormLabel>Phone</FormLabel>
                  <Input type="tel" autoComplete="tel" minH="44px" maxLength={32} value={form.phone || ""} onChange={(e) => setField("phone", e.target.value)} dir="ltr" />
                </FormControl>
              </SimpleGrid>
              <FormControl mt={4} maxW={{ md: "320px" }}>
                <FormLabel>{t("admins.role")}</FormLabel>
                <Select
                  value={form.role}
                  isDisabled={isEditing}
                  onChange={(event) => setField("role", event.target.value as ManagedAdminPayload["role"])}
                >
                  <option value="ADMIN">{t("admins.role.ADMIN")}</option>
                  <option value="SUPER_ADMIN">{t("admins.role.SUPER_ADMIN")}</option>
                </Select>
                <FormHelperText>{t("admins.roleHelp")}</FormHelperText>
              </FormControl>
            </Box>

            <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
              <Text fontWeight="700">{t("admins.limitsSection")}</Text>
              <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.limitsSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5} mt={4}>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>Billing mode</FormLabel>
                  <Select
                    value={form.policy.billing_mode}
                    isDisabled={isEditing}
                    minH="44px"
                    onChange={(event) => setPolicy("billing_mode", event.target.value as AdminPolicy["billing_mode"])}
                  >
                    <option value="LEGACY_COMPAT">Legacy compatibility</option>
                    <option value="SEAT_CREDIT">Seat credit</option>
                    <option value="USED_TRAFFIC">Used traffic</option>
                    <option value="ALLOCATED_TRAFFIC">Allocated traffic</option>
                  </Select>
                  <FormHelperText>Billing mode is immutable after account creation.</FormHelperText>
                </FormControl>
                {form.policy.billing_mode !== "SEAT_CREDIT" && <FormControl isReadOnly={isEditing}>
                  <FormLabel>{t("admins.creditLimit")}</FormLabel>
                  <Input
                    type="number"
                    min={0}
                    step="0.01"
                    dir="ltr"
                    value={form.policy.total_traffic === null ? "" : form.policy.total_traffic / GIB}
                    readOnly={isEditing}
                    onChange={(event) => setPolicy(
                      "total_traffic",
                      event.target.value === "" ? null : Math.round(Number(event.target.value) * GIB)
                    )}
                  />
                  <FormHelperText>
                    {t(isEditing ? "admins.creditLedgerHelp" : "admins.initialCreditLedgerHelp")}
                  </FormHelperText>
                </FormControl>}
                {form.policy.billing_mode === "LEGACY_COMPAT" && <FormControl>
                  <FormLabel>{t("admins.volumeMode")}</FormLabel>
                  <Select
                    value={form.policy.calculate_volume}
                    onChange={(event) => setPolicy(
                      "calculate_volume",
                      event.target.value as AdminPolicy["calculate_volume"]
                    )}
                  >
                    <option value="used_traffic">{t("admins.usedTrafficMode")}</option>
                    <option value="created_traffic">{t("admins.createdTrafficMode")}</option>
                  </Select>
                  <FormHelperText>{t("admins.volumeModeHelp")}</FormHelperText>
                </FormControl>}
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
                {form.policy.billing_mode === "SEAT_CREDIT" && <FormControl isReadOnly={isEditing} isRequired={!isEditing}>
                  <FormLabel>{t("admins.deviceCapacity")}</FormLabel>
                  <Input type="number" min={1} dir="ltr" value={form.policy.device_capacity_limit ?? ""} onChange={(e) => setPolicy("device_capacity_limit", nullableNumber(e))} />
                  <FormHelperText>Initial finite Seat Credit balance.</FormHelperText>
                </FormControl>}
                <FormControl>
                  <FormLabel>{t("admins.maxDuration")}</FormLabel>
                  <Input type="number" min={1} dir="ltr" value={form.policy.max_user_duration_days ?? ""} onChange={(e) => setPolicy("max_user_duration_days", nullableNumber(e))} />
                  <FormHelperText>{t("admins.blankUnlimited")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.expiryDate")}</FormLabel>
                  <Input type="date" dir="ltr" value={form.policy.expiry_date || ""} onChange={(e) => setPolicy("expiry_date", e.target.value || null)} />
                </FormControl>
                {form.policy.calculate_volume === "used_traffic" && (
                  <FormControl isRequired>
                    <FormLabel>{t("admins.adminWarningPercent")}</FormLabel>
                    <Input type="number" min={1} max={100} step={1} dir="ltr" value={form.policy.admin_traffic_warning_percent} onChange={(e) => setPolicy("admin_traffic_warning_percent", Number(e.target.value))} />
                    <FormHelperText>{t("admins.adminWarningPercentHelp")}</FormHelperText>
                  </FormControl>
                )}
                {form.policy.calculate_volume === "used_traffic" && (
                  <FormControl isRequired>
                    <FormLabel>{t("admins.sudoWarningPercent")}</FormLabel>
                    <Input type="number" min={1} max={100} step={1} dir="ltr" value={form.policy.sudo_traffic_warning_percent} onChange={(e) => setPolicy("sudo_traffic_warning_percent", Number(e.target.value))} />
                    <FormHelperText>{t("admins.sudoWarningPercentHelp")}</FormHelperText>
                  </FormControl>
                )}
              </SimpleGrid>
            </Box>

            <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
              <Text fontWeight="700">{t("admins.planCategories")}</Text>
              <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.planCategoriesHelp")}</Text>
              {categoriesQuery.isError ? (
                <Alert status="error" mt={4}><AlertIcon />{t("admins.planCategoriesLoadFailed")}</Alert>
              ) : categoriesQuery.isLoading ? (
                <Skeleton mt={4} h="64px" borderRadius="10px" />
              ) : (categoriesQuery.data || []).length === 0 ? (
                <Text color="gray.400" fontSize="sm" mt={4}>{t("admins.noPlanCategories")}</Text>
              ) : (
                <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={4}>
                  {(categoriesQuery.data || []).map((category) => (
                    <Checkbox
                      key={category.id}
                      minH="48px"
                      px={3}
                      colorScheme="primary"
                      borderWidth="1px"
                      borderColor="rgba(148,163,184,.18)"
                      borderRadius="10px"
                      isChecked={form.plan_category_ids.includes(category.id)}
                      onChange={(event) => togglePlanCategory(category.id, event.target.checked)}
                    >
                      <Text fontSize="sm" fontWeight="650">{category.name}</Text>
                    </Checkbox>
                  ))}
                </SimpleGrid>
              )}
            </Box>

            <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
              <Text fontWeight="700">{t("admins.permissionsSection")}</Text>
              <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.permissionsSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={4}>
                {toggles.map(([key, label, help]) => (
                  <HStack key={key} justify="space-between" align="start" p={4} bg="#111d17" borderWidth="1px" borderColor="#33483b" borderRadius="10px" minW={0}>
                    <Box pe={3} minW={0}>
                      <Text fontSize="sm" fontWeight="650">{t(label)}</Text>
                      <Text fontSize="xs" color="gray.400" mt={1}>{t(help)}</Text>
                    </Box>
                    <Switch flexShrink={0} colorScheme="primary" isChecked={Boolean(form.policy[key])} onChange={(e) => setPolicy(key, e.target.checked as never)} />
                  </HStack>
                ))}
              </SimpleGrid>
            </Box>

            <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
              <Text fontWeight="700">{t("admins.subscriptionModes")}</Text>
              <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.subscriptionModesHelp")}</Text>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={4}>
                {subscriptionModes.map((mode) => (
                  <Checkbox
                    key={mode}
                    minH="52px"
                    px={3}
                    py={2}
                    colorScheme="primary"
                    bg="rgba(255,255,255,.025)"
                    borderWidth="1px"
                    borderColor="rgba(148,163,184,.18)"
                    borderRadius="10px"
                    isChecked={form.policy.allowed_subscription_modes.includes(mode)}
                    onChange={(event) => toggleSubscriptionMode(mode, event.target.checked)}
                  >
                    <Text fontSize="sm" fontWeight="650">{t(`admins.subscriptionMode.${mode}`)}</Text>
                  </Checkbox>
                ))}
              </SimpleGrid>
              <HStack mt={4} justify="space-between" align="start" p={4} bg="#111d17" borderWidth="1px" borderColor="#33483b" borderRadius="10px">
                <Box pe={3} minW={0}>
                  <Text fontSize="sm" fontWeight="650">{t("admins.viewFullClientIp")}</Text>
                  <Text fontSize="xs" color="gray.400" mt={1}>{t("admins.viewFullClientIpHelp")}</Text>
                </Box>
                <Switch
                  flexShrink={0}
                  colorScheme="primary"
                  isChecked={form.policy.view_full_client_ip}
                  onChange={(event) => setPolicy("view_full_client_ip", event.target.checked)}
                />
              </HStack>
            </Box>

            <SimpleGrid columns={{ base: 1, lg: 2 }} gap={5}>
              <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px" minW={0}>
                <Text fontWeight="700">{t("admins.inboundAccess")}</Text>
                <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.inboundAccessHelp")}</Text>
                <Checkbox
                  mt={4}
                  colorScheme="primary"
                  isChecked={form.policy.all_inbounds}
                  onChange={(event) => setPolicy("all_inbounds", event.target.checked)}
                >
                  {t("admins.allInbounds")}
                </Checkbox>
                {!form.policy.all_inbounds && (
                  <Stack mt={4} spacing={3}>
                    <Input
                      aria-label={t("admins.searchInbounds")}
                      value={inboundSearch}
                      onChange={(event) => setInboundSearch(event.target.value)}
                      placeholder={t("admins.searchInbounds")}
                    />
                    <Stack
                      maxH="220px"
                      overflowY="auto"
                      spacing={1}
                      p={2}
                      borderWidth="1px"
                      borderColor="#33483b"
                      borderRadius="10px"
                    >
                      {availableInbounds.map((inbound) => (
                        <Checkbox
                          key={inbound.tag}
                          minH="44px"
                          px={2}
                          colorScheme="primary"
                          isChecked={form.policy.allowed_inbounds.includes(inbound.tag)}
                          onChange={(event) => toggleInbound(inbound.tag, event.target.checked)}
                        >
                          <Text dir="ltr" fontSize="sm" overflowWrap="anywhere">{inbound.tag}</Text>
                        </Checkbox>
                      ))}
                    </Stack>
                  </Stack>
                )}
              </Box>

              <Box p={{ base: 4, md: 5 }} bg="#0d1812" borderWidth="1px" borderColor="#33483b" borderRadius="12px" minW={0}>
                <Text fontWeight="700">{t("admins.allowedUserLimits")}</Text>
                <Text color="gray.400" fontSize="sm" mt={1}>{t("admins.allowedUserLimitsHelp")}</Text>
                <Checkbox
                  mt={4}
                  colorScheme="primary"
                  isChecked={form.policy.all_user_limits}
                  onChange={(event) => setPolicy("all_user_limits", event.target.checked)}
                >
                  {t("admins.allUserLimits")}
                </Checkbox>
                {!form.policy.all_user_limits && (
                  <Stack mt={4} spacing={3}>
                    <HStack align="end">
                      <FormControl>
                        <FormLabel>{t("admins.addUserLimit")}</FormLabel>
                        <Input
                          type="number"
                          min={1}
                          step={1}
                          dir="ltr"
                          value={newUserLimit}
                          onChange={(event) => setNewUserLimit(event.target.value)}
                        />
                      </FormControl>
                      <Button minH="44px" onClick={addUserLimit} isDisabled={!newUserLimit}>{t("add")}</Button>
                    </HStack>
                    <Flex gap={2} wrap="wrap" minH="34px">
                      {form.policy.allowed_user_limits.map((limit) => (
                        <Tag key={limit} colorScheme="yellow" variant="subtle" minH="32px">
                          <TagLabel>{t("admins.userLimitValue", { count: limit })}</TagLabel>
                          <TagCloseButton
                            aria-label={t("remove")}
                            onClick={() => setPolicy(
                              "allowed_user_limits",
                              form.policy.allowed_user_limits.filter((value) => value !== limit)
                            )}
                          />
                        </Tag>
                      ))}
                    </Flex>
                  </Stack>
                )}
              </Box>
            </SimpleGrid>
          </Stack>
        </ModalBody>
        <ModalFooter borderTopWidth="1px" borderColor="#33483b" gap={3} px={{ base: 4, md: 6 }} py={4} flexWrap="wrap">
          <Button minH="44px" flex={{ base: "1 1 140px", sm: "0 0 auto" }} variant="ghost" onClick={onClose}>{t("cancel")}</Button>
          <Button minH="44px" flex={{ base: "1 1 180px", sm: "0 0 auto" }} type="submit" colorScheme="primary" color="#07130e" isLoading={mutation.isLoading}>{t("save")}</Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export const Admins: FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { userData, getUserIsPending } = useGetUser();
  const formDisclosure = useDisclosure();
  const deleteDisclosure = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [selected, setSelected] = useState<ManagedAdmin | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [deleteStrategy, setDeleteStrategy] = useState<"delete_users" | "disable_users" | "keep_users">("keep_users");
  const canManage = userData.is_sudo || userData.role === "OWNER" || userData.role === "SUPER_ADMIN";

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(0);
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const query = useQuery<ManagedAdminList, Error>(
    ["admin-management", page, search],
    () => fetch(`/admin-management?offset=${page * PAGE_SIZE}&limit=${PAGE_SIZE}&username=${encodeURIComponent(search)}`),
    { keepPreviousData: true, enabled: canManage, refetchInterval: 15000 }
  );

  const removeMutation = useMutation(
    ({ username, strategy }: { username: string; strategy: typeof deleteStrategy }) => fetch(`/admin/${username}`, { method: "DELETE", body: { strategy } }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-management");
        toast({ title: t("admins.deleted"), status: "success", duration: 3000 });
        deleteDisclosure.onClose();
      },
      onError: (error) => {
        toast({ title: t("admins.deleteFailed"), description: getErrorMessage(error), status: "error", duration: 5000 });
      },
    }
  );

  if (!getUserIsPending && !canManage) return <Navigate to="/" replace />;

  const admins = query.data?.admins || [];
  const total = query.data?.total || 0;
  const managerCount = admins.filter((item) => item.role === "OWNER" || item.role === "SUPER_ADMIN").length;
  const restrictedCount = admins.filter((item) => Object.entries(item.policy).some(([key, value]) => key.startsWith("prevent_") && value)).length;
  const canEdit = (item: ManagedAdmin) => item.role !== "OWNER" || item.username === userData.username;
  const openCreate = () => { setSelected(null); formDisclosure.onOpen(); };
  const openEdit = (item: ManagedAdmin) => { setSelected(item); formDisclosure.onOpen(); };
  const openDelete = (item: ManagedAdmin) => { setSelected(item); setDeleteStrategy("keep_users"); deleteDisclosure.onOpen(); };

  return (
    <AppShell>
        <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} mb={6} gap={4}>
          <Box>
            <Text color="primary.300" fontSize="xs" fontWeight="800">آزمایشگاه کنترل</Text>
            <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em" mt={1}>{t("admins.title")}</Text>
            <Text color="gray.300" mt={1} maxW="650px">{t("admins.subtitle")}</Text>
          </Box>
          <Button colorScheme="primary" color="#07130e" leftIcon={<AddIcon />} onClick={openCreate}>{t("admins.create")}</Button>
        </Stack>

        <SimpleGrid columns={{ base: 1, sm: 3 }} gap={4} mb={5}>
          <AdminStat label={t("admins.totalAdmins")} value={total} icon={<AdminsIcon />} />
          <AdminStat label={t("admins.managerAdmins")} value={managerCount} icon={<SudoIcon />} />
          <AdminStat label={t("admins.restrictedAdmins")} value={restrictedCount} icon={<ShieldCheckIcon width={20} />} />
        </SimpleGrid>

        <AdminHierarchyPanel />

        <Card variant="outline" bg="#111d17" color="gray.100" borderRadius={{ base: "16px", md: "20px" }} borderColor="#33483b" boxShadow="panel" overflow="hidden">
          <HStack p={4} justify="space-between" borderBottomWidth="1px" borderColor="#33483b" flexWrap="wrap" gap={3}>
            <InputGroup maxW={{ base: "full", md: "360px" }}>
              <InputLeftElement pointerEvents="none" color="gray.400"><SearchIcon /></InputLeftElement>
              <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("admins.search")} />
            </InputGroup>
            <Button size="sm" variant="outline" color="gray.200" borderColor="#475f50" _hover={{ bg: "whiteAlpha.100", borderColor: "primary.400" }} onClick={() => query.refetch()} isLoading={query.isFetching}>{t("refresh")}</Button>
          </HStack>

          {query.isError && (
            <Alert status="error" m={4} w="auto"><AlertIcon />{t("admins.loadFailed")}<Button ms="auto" size="sm" onClick={() => query.refetch()}>{t("retry")}</Button></Alert>
          )}

          {query.isLoading ? (
            <Stack p={5}>{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} startColor="#16251c" endColor="#24392d" height="54px" borderRadius="8px" />)}</Stack>
          ) : admins.length === 0 ? (
            <VStack py={16} px={5} spacing={3}><Box p={3} color="primary.300" borderRadius="full" bg="rgba(72, 213, 139, .12)"><AdminsIcon /></Box><Text color="white" fontWeight="700">{t("admins.empty")}</Text><Text color="gray.400" fontSize="sm" textAlign="center">{t(search ? "admins.emptySearch" : "admins.emptyHelp")}</Text></VStack>
          ) : (
            <>
              <TableContainer display={{ base: "none", lg: "block" }}>
                <Table size="sm">
                  <Thead><Tr><Th>{t("admins.admin")}</Th><Th>{t("admins.access")}</Th><Th>{t("admins.usersCount")}</Th><Th>{t("admins.creditRemaining")}</Th><Th>{t("admins.operationRemaining")}</Th><Th>{t("admins.maxDuration")}</Th><Th>{t("admins.expiryDate")}</Th><Th textAlign="end">{t("admins.actions")}</Th></Tr></Thead>
                  <Tbody>{admins.map((item) => (
                    <Tr key={item.username}>
                      <Td><Text color="white" fontWeight="650">{item.username}</Text><Text fontSize="xs" color="gray.400">{item.phone || t("admins.noContact")}</Text></Td>
                      <Td><Stack align="start" spacing={1}><Badge colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge><Badge variant="outline">{item.policy.billing_mode}</Badge></Stack></Td>
                      <Td>{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Td>
                      <Td><CreditRemaining admin={item} /></Td>
                      <Td>{item.quota.operation_allowance_remaining ?? t("unlimited")}</Td>
                      <Td>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Td>
                      <Td>{item.policy.expiry_date || t("unlimited")}</Td>
                      <Td><HStack justify="end"><IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} /><IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.role === "OWNER"} onClick={() => openDelete(item)} /></HStack></Td>
                    </Tr>
                  ))}</Tbody>
                </Table>
              </TableContainer>

              <Stack display={{ base: "flex", lg: "none" }} divider={<Divider borderColor="#33483b" />} spacing={0}>
                {admins.map((item) => (
                  <Box key={item.username} p={4}>
                    <HStack justify="space-between" align="start"><Box><Text color="white" fontWeight="700">{item.username}</Text><Badge mt={1} colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge></Box><HStack><IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} /><IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.role === "OWNER"} onClick={() => openDelete(item)} /></HStack></HStack>
                    <SimpleGrid columns={2} gap={3} mt={4} fontSize="sm"><Box><Text color="gray.400" fontSize="xs">{t("admins.usersCount")}</Text><Text color="gray.100" mt={1}>{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Text></Box><Box><Text color="gray.400" fontSize="xs">{t("admins.creditRemaining")}</Text><Box mt={1}><CreditRemaining admin={item} /></Box></Box><Box><Text color="gray.400" fontSize="xs">{t("admins.operationRemaining")}</Text><Text color="gray.100" mt={1}>{item.quota.operation_allowance_remaining ?? t("unlimited")}</Text></Box><Box><Text color="gray.400" fontSize="xs">{t("admins.maxDuration")}</Text><Text color="gray.100" mt={1}>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Text></Box><Box><Text color="gray.400" fontSize="xs">{t("admins.expiryDate")}</Text><Text color="gray.100" mt={1}>{item.policy.expiry_date || t("unlimited")}</Text></Box></SimpleGrid>
                  </Box>
                ))}
              </Stack>
            </>
          )}

          {total > PAGE_SIZE && (
            <HStack justify="space-between" p={4} borderTopWidth="1px" borderColor="#33483b"><Text fontSize="sm" color="gray.400">{t("admins.page", { current: page + 1, total: Math.ceil(total / PAGE_SIZE) })}</Text><HStack><Button size="sm" variant="outline" borderColor="#475f50" isDisabled={page === 0} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button><Button size="sm" variant="outline" borderColor="#475f50" isDisabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button></HStack></HStack>
          )}
        </Card>
        <AdminFormModal isOpen={formDisclosure.isOpen} admin={selected} onClose={formDisclosure.onClose} />
        <AlertDialog isOpen={deleteDisclosure.isOpen} leastDestructiveRef={cancelRef} onClose={deleteDisclosure.onClose}>
          <AlertDialogOverlay bg="rgba(0, 0, 0, .72)"><AlertDialogContent bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="12px"><AlertDialogHeader>{t("admins.deleteTitle")}</AlertDialogHeader><AlertDialogBody><Text mb={3}>{t("admins.deleteConfirm", { username: selected?.username })}</Text><FormControl><FormLabel>{t("admins.deleteStrategy")}</FormLabel><Select value={deleteStrategy} onChange={(event) => setDeleteStrategy(event.target.value as typeof deleteStrategy)}><option value="keep_users">{t("admins.keepUsers")}</option><option value="disable_users">{t("admins.disableUsers")}</option><option value="delete_users">{t("admins.deleteUsers")}</option></Select><FormHelperText>{t(`admins.deleteStrategyHelp.${deleteStrategy}`)}</FormHelperText></FormControl></AlertDialogBody><AlertDialogFooter borderTopWidth="1px" borderColor="#33483b" gap={3}><Button ref={cancelRef} variant="ghost" onClick={deleteDisclosure.onClose}>{t("cancel")}</Button><Button colorScheme="red" isLoading={removeMutation.isLoading} onClick={() => selected && removeMutation.mutate({ username: selected.username, strategy: deleteStrategy })}>{t("delete")}</Button></AlertDialogFooter></AlertDialogContent></AlertDialogOverlay>
        </AlertDialog>
    </AppShell>
  );
};

export default Admins;
