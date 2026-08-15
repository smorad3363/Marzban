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
import useGetUser from "hooks/useGetUser";
import { ChangeEvent, FC, FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { AdminPolicy, ManagedAdmin, ManagedAdminList, ManagedAdminPayload } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const SearchIcon = chakra(MagnifyingGlassIcon, { baseStyle: { w: 4, h: 4 } });
const AddIcon = chakra(PlusIcon, { baseStyle: { w: 4, h: 4 } });
const EditIcon = chakra(PencilSquareIcon, { baseStyle: { w: 4, h: 4 } });
const RemoveIcon = chakra(TrashIcon, { baseStyle: { w: 4, h: 4 } });
const AdminsIcon = chakra(UserGroupIcon, { baseStyle: { w: 5, h: 5 } });
const SudoIcon = chakra(ShieldCheckIcon, { baseStyle: { w: 5, h: 5 } });

const PAGE_SIZE = 20;
const GIB = 1024 ** 3;

const emptyPolicy = (): AdminPolicy => ({
  total_traffic: null,
  used_traffic: 0,
  expiry_date: null,
  user_limit: null,
  max_users: null,
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
  telegram_id: null,
  discord_webhook: null,
  policy: emptyPolicy(),
});

const getErrorMessage = (error: any) =>
  error?.data?.detail || error?.response?._data?.detail || error?.message;

type StatProps = { label: string; value: string | number; icon: JSX.Element };
const AdminStat: FC<StatProps> = ({ label, value, icon }) => (
  <Card variant="outline" p={5} boxShadow="panel" borderRadius="18px" borderColor="gray.200" _dark={{ borderColor: "whiteAlpha.200" }}>
    <HStack justify="space-between">
      <Box>
        <Text color="gray.500" fontSize="sm" fontWeight="600">{label}</Text>
        <Text mt={1} fontSize="2xl" fontWeight="750">{value}</Text>
      </Box>
      <Box color="primary.600" bg="primary.50" _dark={{ bg: "whiteAlpha.100", color: "primary.300" }} p={3} borderRadius="12px">
        {icon}
      </Box>
    </HStack>
  </Card>
);

type FormModalProps = {
  isOpen: boolean;
  admin: ManagedAdmin | null;
  onClose: () => void;
};

const AdminFormModal: FC<FormModalProps> = ({ isOpen, admin, onClose }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ManagedAdminPayload>(emptyAdmin());
  const isEditing = Boolean(admin);

  useEffect(() => {
    setForm(admin ? {
      username: admin.username,
      password: "",
      is_sudo: admin.is_sudo,
      telegram_id: admin.telegram_id,
      discord_webhook: admin.discord_webhook,
      policy: { ...admin.policy },
    } : emptyAdmin());
  }, [admin, isOpen]);

  const mutation = useMutation(
    (payload: ManagedAdminPayload) =>
      fetch(isEditing ? `/admin-management/${admin?.username}` : "/admin-management", {
        method: isEditing ? "PUT" : "POST",
        body: payload,
      }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-management");
        toast({ title: t(isEditing ? "admins.updated" : "admins.created"), status: "success", duration: 3000 });
        onClose();
      },
      onError: (error) => {
        toast({ title: t("admins.saveFailed"), description: getErrorMessage(error), status: "error", duration: 5000 });
      },
    }
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
    const payload = { ...form };
    if (isEditing && !payload.password) delete payload.password;
    mutation.mutate(payload);
  };

  const toggles: Array<[keyof AdminPolicy, string, string]> = [
    ["prevent_user_creation", "admins.preventCreate", "admins.preventCreateHelp"],
    ["prevent_user_deletion", "admins.preventDelete", "admins.preventDeleteHelp"],
    ["prevent_user_reset", "admins.preventReset", "admins.preventResetHelp"],
    ["prevent_revoke_subscription", "admins.preventRevoke", "admins.preventRevokeHelp"],
    ["prevent_unlimited_traffic", "admins.preventUnlimited", "admins.preventUnlimitedHelp"],
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay bg="blackAlpha.500" />
      <ModalContent as="form" onSubmit={submit} borderRadius="14px">
        <ModalHeader>{t(isEditing ? "admins.editTitle" : "admins.createTitle")}</ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={7}>
          <Stack spacing={7}>
            <Box>
              <Text fontWeight="700">{t("admins.accountSection")}</Text>
              <Text color="gray.500" fontSize="sm" mt={1}>{t("admins.accountSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={4} mt={4}>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>{t("admins.username")}</FormLabel>
                  <Input value={form.username} disabled={isEditing} maxLength={34} onChange={(e) => setField("username", e.target.value)} />
                </FormControl>
                <FormControl isRequired={!isEditing}>
                  <FormLabel>{t("admins.password")}</FormLabel>
                  <Input type="password" value={form.password || ""} placeholder={isEditing ? t("admins.passwordKeep") : ""} onChange={(e) => setField("password", e.target.value)} />
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.telegramId")}</FormLabel>
                  <Input type="number" value={form.telegram_id ?? ""} onChange={(e) => setField("telegram_id", nullableNumber(e))} />
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.discordWebhook")}</FormLabel>
                  <Input value={form.discord_webhook || ""} onChange={(e) => setField("discord_webhook", e.target.value || null)} dir="ltr" />
                </FormControl>
              </SimpleGrid>
              <Checkbox mt={4} colorScheme="primary" isChecked={form.is_sudo} onChange={(e) => setField("is_sudo", e.target.checked)}>
                {t("admins.sudoAccess")}
              </Checkbox>
            </Box>

            <Divider />
            <Box>
              <Text fontWeight="700">{t("admins.limitsSection")}</Text>
              <Text color="gray.500" fontSize="sm" mt={1}>{t("admins.limitsSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4} mt={4}>
                <FormControl>
                  <FormLabel>{t("admins.totalTraffic")}</FormLabel>
                  <Input type="number" min={0} step="0.01" value={form.policy.total_traffic === null ? "" : form.policy.total_traffic / GIB} onChange={(e) => setPolicy("total_traffic", e.target.value === "" ? null : Math.round(Number(e.target.value) * GIB))} />
                  <FormHelperText>{t("admins.blankUnlimited")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.operationLimit")}</FormLabel>
                  <Input type="number" min={0} value={form.policy.user_limit ?? ""} onChange={(e) => setPolicy("user_limit", nullableNumber(e))} />
                  <FormHelperText>{t("admins.operationLimitHelp")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.maxUsers")}</FormLabel>
                  <Input type="number" min={1} value={form.policy.max_users ?? ""} onChange={(e) => setPolicy("max_users", nullableNumber(e))} />
                  <FormHelperText>{t("admins.maxUsersHelp")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.maxDuration")}</FormLabel>
                  <Input type="number" min={1} value={form.policy.max_user_duration_days ?? ""} onChange={(e) => setPolicy("max_user_duration_days", nullableNumber(e))} />
                  <FormHelperText>{t("admins.blankUnlimited")}</FormHelperText>
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.expiryDate")}</FormLabel>
                  <Input type="date" value={form.policy.expiry_date || ""} onChange={(e) => setPolicy("expiry_date", e.target.value || null)} />
                </FormControl>
                <FormControl>
                  <FormLabel>{t("admins.volumeMode")}</FormLabel>
                  <Select value={form.policy.calculate_volume} onChange={(e) => setPolicy("calculate_volume", e.target.value as AdminPolicy["calculate_volume"])}>
                    <option value="used_traffic">{t("admins.usedTrafficMode")}</option>
                    <option value="created_traffic">{t("admins.createdTrafficMode")}</option>
                  </Select>
                </FormControl>
              </SimpleGrid>
            </Box>

            <Divider />
            <Box>
              <Text fontWeight="700">{t("admins.permissionsSection")}</Text>
              <Text color="gray.500" fontSize="sm" mt={1}>{t("admins.permissionsSectionHelp")}</Text>
              <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={4}>
                {toggles.map(([key, label, help]) => (
                  <HStack key={key} justify="space-between" align="start" p={4} borderWidth="1px" borderRadius="10px">
                    <Box pe={3}>
                      <Text fontSize="sm" fontWeight="650">{t(label)}</Text>
                      <Text fontSize="xs" color="gray.500" mt={1}>{t(help)}</Text>
                    </Box>
                    <Switch colorScheme="primary" isChecked={Boolean(form.policy[key])} onChange={(e) => setPolicy(key, e.target.checked as never)} />
                  </HStack>
                ))}
              </SimpleGrid>
            </Box>
          </Stack>
        </ModalBody>
        <ModalFooter borderTopWidth="1px" gap={3}>
          <Button variant="ghost" onClick={onClose}>{t("cancel")}</Button>
          <Button type="submit" colorScheme="primary" isLoading={mutation.isLoading}>{t("save")}</Button>
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
    { keepPreviousData: true, enabled: userData.is_sudo }
  );

  const removeMutation = useMutation(
    (username: string) => fetch(`/admin/${username}`, { method: "DELETE" }),
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

  if (!getUserIsPending && !userData.is_sudo) return <Navigate to="/" replace />;

  const admins = query.data?.admins || [];
  const total = query.data?.total || 0;
  const sudoCount = admins.filter((item) => item.is_sudo).length;
  const restrictedCount = admins.filter((item) => Object.entries(item.policy).some(([key, value]) => key.startsWith("prevent_") && value)).length;
  const canEdit = (item: ManagedAdmin) => !item.is_sudo || item.username === userData.username;
  const openCreate = () => { setSelected(null); formDisclosure.onOpen(); };
  const openEdit = (item: ManagedAdmin) => { setSelected(item); formDisclosure.onOpen(); };
  const openDelete = (item: ManagedAdmin) => { setSelected(item); deleteDisclosure.onOpen(); };

  return (
    <AppShell>
        <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} mb={6} gap={4}>
          <Box>
            <Text color="primary.600" _dark={{ color: "primary.300" }} fontSize="xs" fontWeight="800" letterSpacing="0.13em" textTransform="uppercase">Dashboard</Text>
            <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em" mt={1}>{t("admins.title")}</Text>
            <Text color="gray.500" mt={1} maxW="650px">{t("admins.subtitle")}</Text>
          </Box>
          <Button colorScheme="primary" leftIcon={<AddIcon />} onClick={openCreate}>{t("admins.create")}</Button>
        </Stack>

        <SimpleGrid columns={{ base: 1, sm: 3 }} gap={4} mb={5}>
          <AdminStat label={t("admins.totalAdmins")} value={total} icon={<AdminsIcon />} />
          <AdminStat label={t("admins.sudoAdmins")} value={sudoCount} icon={<SudoIcon />} />
          <AdminStat label={t("admins.restrictedAdmins")} value={restrictedCount} icon={<ShieldCheckIcon width={20} />} />
        </SimpleGrid>

        <Card variant="outline" borderRadius={{ base: "16px", md: "20px" }} borderColor="gray.200" _dark={{ borderColor: "whiteAlpha.200" }} boxShadow="panel" overflow="hidden">
          <HStack p={4} justify="space-between" borderBottomWidth="1px" flexWrap="wrap" gap={3}>
            <InputGroup maxW={{ base: "full", md: "360px" }}>
              <InputLeftElement pointerEvents="none"><SearchIcon /></InputLeftElement>
              <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("admins.search")} />
            </InputGroup>
            <Button size="sm" variant="outline" onClick={() => query.refetch()} isLoading={query.isFetching}>{t("refresh")}</Button>
          </HStack>

          {query.isError && (
            <Alert status="error" m={4} w="auto"><AlertIcon />{t("admins.loadFailed")}<Button ms="auto" size="sm" onClick={() => query.refetch()}>{t("retry")}</Button></Alert>
          )}

          {query.isLoading ? (
            <Stack p={5}>{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} height="54px" borderRadius="8px" />)}</Stack>
          ) : admins.length === 0 ? (
            <VStack py={16} px={5} spacing={3}><Box p={3} borderRadius="full" bg="gray.100" _dark={{ bg: "whiteAlpha.100" }}><AdminsIcon /></Box><Text fontWeight="700">{t("admins.empty")}</Text><Text color="gray.500" fontSize="sm" textAlign="center">{t(search ? "admins.emptySearch" : "admins.emptyHelp")}</Text></VStack>
          ) : (
            <>
              <TableContainer display={{ base: "none", lg: "block" }}>
                <Table size="sm">
                  <Thead><Tr><Th>{t("admins.admin")}</Th><Th>{t("admins.access")}</Th><Th>{t("admins.usersCount")}</Th><Th>{t("admins.credit")}</Th><Th>{t("admins.operationLimit")}</Th><Th>{t("admins.maxDuration")}</Th><Th>{t("admins.expiryDate")}</Th><Th textAlign="end">{t("admins.actions")}</Th></Tr></Thead>
                  <Tbody>{admins.map((item) => (
                    <Tr key={item.username}>
                      <Td><Text fontWeight="650">{item.username}</Text><Text fontSize="xs" color="gray.500">{item.telegram_id ? `Telegram: ${item.telegram_id}` : t("admins.noContact")}</Text></Td>
                      <Td><Badge colorScheme={item.is_sudo ? "purple" : "gray"}>{t(item.is_sudo ? "admins.sudo" : "admins.adminRole")}</Badge></Td>
                      <Td>{item.user_count} / {item.policy.max_users ?? t("unlimited")}</Td>
                      <Td>{item.policy.total_traffic === null ? t("unlimited") : formatBytes(Math.max(item.policy.total_traffic - item.policy.used_traffic, 0))}</Td>
                      <Td>{item.policy.user_limit ?? t("unlimited")}</Td>
                      <Td>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Td>
                      <Td>{item.policy.expiry_date || t("unlimited")}</Td>
                      <Td><HStack justify="end"><IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} /><IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.is_sudo} onClick={() => openDelete(item)} /></HStack></Td>
                    </Tr>
                  ))}</Tbody>
                </Table>
              </TableContainer>

              <Stack display={{ base: "flex", lg: "none" }} divider={<Divider />} spacing={0}>
                {admins.map((item) => (
                  <Box key={item.username} p={4}>
                    <HStack justify="space-between" align="start"><Box><Text fontWeight="700">{item.username}</Text><Badge mt={1} colorScheme={item.is_sudo ? "purple" : "gray"}>{t(item.is_sudo ? "admins.sudo" : "admins.adminRole")}</Badge></Box><HStack><IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} /><IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.is_sudo} onClick={() => openDelete(item)} /></HStack></HStack>
                    <SimpleGrid columns={2} gap={3} mt={4} fontSize="sm"><Box><Text color="gray.500" fontSize="xs">{t("admins.usersCount")}</Text><Text mt={1}>{item.user_count} / {item.policy.max_users ?? t("unlimited")}</Text></Box><Box><Text color="gray.500" fontSize="xs">{t("admins.credit")}</Text><Text mt={1}>{item.policy.total_traffic === null ? t("unlimited") : formatBytes(Math.max(item.policy.total_traffic - item.policy.used_traffic, 0))}</Text></Box><Box><Text color="gray.500" fontSize="xs">{t("admins.operationLimit")}</Text><Text mt={1}>{item.policy.user_limit ?? t("unlimited")}</Text></Box><Box><Text color="gray.500" fontSize="xs">{t("admins.maxDuration")}</Text><Text mt={1}>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Text></Box><Box><Text color="gray.500" fontSize="xs">{t("admins.expiryDate")}</Text><Text mt={1}>{item.policy.expiry_date || t("unlimited")}</Text></Box></SimpleGrid>
                  </Box>
                ))}
              </Stack>
            </>
          )}

          {total > PAGE_SIZE && (
            <HStack justify="space-between" p={4} borderTopWidth="1px"><Text fontSize="sm" color="gray.500">{t("admins.page", { current: page + 1, total: Math.ceil(total / PAGE_SIZE) })}</Text><HStack><Button size="sm" variant="outline" isDisabled={page === 0} onClick={() => setPage((value) => value - 1)}>{t("previous")}</Button><Button size="sm" variant="outline" isDisabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((value) => value + 1)}>{t("next")}</Button></HStack></HStack>
          )}
        </Card>
        <AdminFormModal isOpen={formDisclosure.isOpen} admin={selected} onClose={formDisclosure.onClose} />
        <AlertDialog isOpen={deleteDisclosure.isOpen} leastDestructiveRef={cancelRef} onClose={deleteDisclosure.onClose}>
          <AlertDialogOverlay><AlertDialogContent borderRadius="12px"><AlertDialogHeader>{t("admins.deleteTitle")}</AlertDialogHeader><AlertDialogBody>{t("admins.deleteConfirm", { username: selected?.username })}</AlertDialogBody><AlertDialogFooter gap={3}><Button ref={cancelRef} onClick={deleteDisclosure.onClose}>{t("cancel")}</Button><Button colorScheme="red" isLoading={removeMutation.isLoading} onClick={() => selected && removeMutation.mutate(selected.username)}>{t("delete")}</Button></AlertDialogFooter></AlertDialogContent></AlertDialogOverlay>
        </AlertDialog>
    </AppShell>
  );
};

export default Admins;
