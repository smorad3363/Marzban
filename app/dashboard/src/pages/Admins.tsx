import {
  Alert, AlertDialog, AlertDialogBody, AlertDialogContent, AlertDialogFooter,
  AlertDialogHeader, AlertDialogOverlay, AlertIcon, Badge, Box, Button, Card,
  Divider, FormControl, FormHelperText, FormLabel, HStack, IconButton, Input,
  InputGroup, InputLeftElement, Select, SimpleGrid, Skeleton, Stack, Table,
  TableContainer, Tbody, Td, Text, Th, Thead, Tr, VStack, chakra,
  useDisclosure, useToast,
} from "@chakra-ui/react";
import {
  MagnifyingGlassIcon, PencilSquareIcon, PlusIcon, ShieldCheckIcon,
  TrashIcon, UserGroupIcon,
} from "@heroicons/react/24/outline";
import { AdminFormDrawer } from "components/AdminFormDrawer";
import { AdminHierarchyPanel } from "components/AdminHierarchyPanel";
import { AppShell } from "components/AppShell";
import useGetUser from "hooks/useGetUser";
import { FC, Fragment, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { Navigate } from "react-router-dom";
import { fetch } from "service/http";
import { ManagedAdmin, ManagedAdminList } from "types/Admin";
import { localizedApiError } from "utils/apiError";
import { formatBytes } from "utils/formatByte";

const SearchIcon = chakra(MagnifyingGlassIcon, { baseStyle: { w: 4, h: 4 } });
const AddIcon = chakra(PlusIcon, { baseStyle: { w: 4, h: 4 } });
const EditIcon = chakra(PencilSquareIcon, { baseStyle: { w: 4, h: 4 } });
const RemoveIcon = chakra(TrashIcon, { baseStyle: { w: 4, h: 4 } });
const AdminsIcon = chakra(UserGroupIcon, { baseStyle: { w: 5, h: 5 } });
const SudoIcon = chakra(ShieldCheckIcon, { baseStyle: { w: 5, h: 5 } });
const PAGE_SIZE = 20;

const billingModeLabels: Record<string, string> = {
  LEGACY_COMPAT: "حالت قدیمی",
  SEAT_CREDIT: "اعتبار دستگاه",
  USED_TRAFFIC: "مصرف واقعی",
  ALLOCATED_TRAFFIC: "حجم اختصاصی",
};

const CreditRemaining: FC<{ admin: ManagedAdmin }> = ({ admin }) => {
  const { t } = useTranslation();
  const quota = admin.quota;
  return (
    <Stack spacing={1} align="start">
      <Text>
        {quota.credit_remaining === null
          ? t("unlimited")
          : admin.policy.billing_mode === "SEAT_CREDIT"
            ? `${quota.credit_remaining} دستگاه`
            : formatBytes(quota.credit_remaining)}
      </Text>
      {quota.credit_usage_percent !== null && (
        <HStack spacing={2}>
          <Text fontSize="xs" color="gray.400">{quota.credit_usage_percent}%</Text>
          {quota.sudo_warning_active && <Badge colorScheme="orange" variant="subtle">{t("admins.creditWarning")}</Badge>}
        </HStack>
      )}
    </Stack>
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
  const [expandedUsername, setExpandedUsername] = useState<string | null>(null);
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
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "center" }} mb={5} gap={4}>
        <Box>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-0.035em">{t("admins.title")}</Text>
          <Text color="gray.300" mt={1} maxW="650px">{t("admins.subtitle")}</Text>
        </Box>
        <Button minH="44px" flexShrink={0} colorScheme="primary" color="#07130e" leftIcon={<AddIcon />} onClick={openCreate}>{t("admins.create")}</Button>
      </Stack>

      <Card mb={5} p={{ base: 3, md: 4 }} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="16px" boxShadow="panel">
        <SimpleGrid columns={{ base: 1, sm: 3 }} gap={{ base: 2, sm: 0 }}>
          {[
            [t("admins.totalAdmins"), total, <AdminsIcon key="admins" />],
            [t("admins.managerAdmins"), managerCount, <SudoIcon key="managers" />],
            [t("admins.restrictedAdmins"), restrictedCount, <ShieldCheckIcon key="restricted" width={20} />],
          ].map(([label, value, icon], index) => (
            <HStack key={String(label)} px={{ base: 2, sm: 4 }} py={2} borderInlineStartWidth={{ base: 0, sm: index ? "1px" : 0 }} borderColor="#33483b">
              <Box color="primary.300" p={2} bg="rgba(72, 213, 139, .10)" borderRadius="10px">{icon}</Box>
              <Box>
                <Text color="gray.400" fontSize="xs" fontWeight="650">{label}</Text>
                <Text color="white" mt={0.5} fontSize="xl" fontWeight="800">{value}</Text>
              </Box>
            </HStack>
          ))}
        </SimpleGrid>
      </Card>

      <AdminHierarchyPanel />

      <Card variant="outline" bg="#111d17" color="gray.100" borderRadius={{ base: "16px", md: "20px" }} borderColor="#33483b" boxShadow="panel" overflow="hidden">
        <Stack direction={{ base: "column", md: "row" }} p={4} justify="space-between" align={{ md: "center" }} borderBottomWidth="1px" borderColor="#33483b" gap={3}>
          <Box>
            <Text as="h2" fontWeight="800">فهرست ادمین‌ها</Text>
            <Text mt={1} fontSize="xs" color="gray.400">اطلاعات اصلی هر ادمین را می‌بینید. برای بقیه موارد، جزئیات را باز کنید.</Text>
          </Box>
          <HStack w={{ base: "full", md: "auto" }} flexWrap="wrap">
            <InputGroup flex="1" minW={{ base: "full", md: "260px" }} maxW={{ md: "360px" }}>
              <InputLeftElement pointerEvents="none" color="gray.400"><SearchIcon /></InputLeftElement>
              <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder={t("admins.search")} />
            </InputGroup>
            <Button size="sm" minH="40px" variant="outline" color="gray.200" borderColor="#475f50" _hover={{ bg: "whiteAlpha.100", borderColor: "primary.400" }} onClick={() => query.refetch()} isLoading={query.isFetching}>{t("refresh")}</Button>
          </HStack>
        </Stack>

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
                <Thead><Tr><Th>{t("admins.admin")}</Th><Th>{t("admins.access")}</Th><Th>{t("admins.usersCount")}</Th><Th>{t("admins.creditRemaining")}</Th><Th textAlign="end">{t("admins.actions")}</Th></Tr></Thead>
                <Tbody>{admins.map((item) => (
                  <Fragment key={item.username}>
                    <Tr bg={expandedUsername === item.username ? "whiteAlpha.50" : undefined}>
                      <Td><Text color="white" fontWeight="650" dir="ltr">{item.username}</Text><Text fontSize="xs" color="gray.400" dir="ltr">{item.phone || t("admins.noContact")}</Text></Td>
                      <Td><Stack align="start" spacing={1}><Badge colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge><Badge variant="outline">{billingModeLabels[item.policy.billing_mode] || item.policy.billing_mode}</Badge></Stack></Td>
                      <Td>{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Td>
                      <Td><CreditRemaining admin={item} /></Td>
                      <Td>
                        <HStack justify="end">
                          <Button size="sm" variant="ghost" minH="36px" aria-expanded={expandedUsername === item.username} onClick={() => setExpandedUsername((current) => current === item.username ? null : item.username)}>{expandedUsername === item.username ? "بستن" : "جزئیات"}</Button>
                          <IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} />
                          <IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.role === "OWNER"} onClick={() => openDelete(item)} />
                        </HStack>
                      </Td>
                    </Tr>
                    {expandedUsername === item.username && (
                      <Tr bg="blackAlpha.200">
                        <Td colSpan={5} py={4}>
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
                <Box key={item.username} p={4}>
                  <HStack justify="space-between" align="start">
                    <Box><Text color="white" fontWeight="700" dir="ltr">{item.username}</Text><Badge mt={1} colorScheme={item.role === "OWNER" ? "purple" : item.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{t(`admins.role.${item.role}`)}</Badge></Box>
                    <HStack><IconButton aria-label={t("edit")} size="sm" variant="ghost" icon={<EditIcon />} isDisabled={!canEdit(item)} onClick={() => openEdit(item)} /><IconButton aria-label={t("delete")} size="sm" variant="ghost" colorScheme="red" icon={<RemoveIcon />} isDisabled={item.role === "OWNER"} onClick={() => openDelete(item)} /></HStack>
                  </HStack>
                  <SimpleGrid columns={2} gap={3} mt={4} fontSize="sm">
                    <Box><Text color="gray.400" fontSize="xs">{t("admins.usersCount")}</Text><Text color="gray.100" mt={1}>{item.quota.current_users} / {item.quota.max_users ?? t("unlimited")}</Text></Box>
                    <Box><Text color="gray.400" fontSize="xs">{t("admins.creditRemaining")}</Text><Box mt={1}><CreditRemaining admin={item} /></Box></Box>
                    <Box><Text color="gray.400" fontSize="xs">{t("admins.operationRemaining")}</Text><Text color="gray.100" mt={1}>{item.quota.operation_allowance_remaining ?? t("unlimited")}</Text></Box>
                    <Box><Text color="gray.400" fontSize="xs">{t("admins.maxDuration")}</Text><Text color="gray.100" mt={1}>{item.policy.max_user_duration_days ? `${item.policy.max_user_duration_days} ${t("days")}` : t("unlimited")}</Text></Box>
                  </SimpleGrid>
                  <Button mt={3} w="full" minH="40px" size="sm" variant="ghost" aria-expanded={expandedUsername === item.username} onClick={() => setExpandedUsername((current) => current === item.username ? null : item.username)}>{expandedUsername === item.username ? "بستن جزئیات" : "نمایش جزئیات بیشتر"}</Button>
                  {expandedUsername === item.username && (
                    <SimpleGrid columns={2} gap={3} mt={3} pt={3} borderTopWidth="1px" borderColor="#33483b" fontSize="sm">
                      <Box><Text color="gray.400" fontSize="xs">{t("admins.expiryDate")}</Text><Text color="gray.100" mt={1} dir="ltr">{item.policy.expiry_date || t("unlimited")}</Text></Box>
                      <Box><Text color="gray.400" fontSize="xs">نوع اعتبار</Text><Text color="gray.100" mt={1}>{billingModeLabels[item.policy.billing_mode] || item.policy.billing_mode}</Text></Box>
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
    </AppShell>
  );
};

export default Admins;
