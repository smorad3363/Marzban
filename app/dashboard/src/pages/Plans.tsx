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
  FormControl,
  FormHelperText,
  FormLabel,
  HStack,
  Input,
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
  Text,
  Textarea,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import { AppShell } from "components/AppShell";
import useGetUser from "hooks/useGetUser";
import { FC, FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { AccountSummary, PlanCategory, PlanNetworkOption, UserPlan } from "types/Admin";
import { formatBytes } from "utils/formatByte";
import { localizedApiError } from "utils/apiError";
import {
  missingPlanInboundTags,
  missingPlanHostIds,
  normalizePlanInboundTags,
  normalizePlanHostScope,
  togglePlanHostId,
  togglePlanInboundTag,
} from "utils/planInbounds";

const GIB = 1024 ** 3;

type PlanDraft = {
  name: string;
  description: string;
  dataGiB: string;
  durationDays: string;
  deviceLimit: string;
  resetStrategy: "no_reset" | "day" | "week" | "month" | "year";
  inbounds: string[];
  hosts: Record<string, number[]>;
  categoryId: string;
  isTrial: boolean;
};

const emptyDraft = (): PlanDraft => ({
  name: "",
  description: "",
  dataGiB: "10",
  durationDays: "30",
  deviceLimit: "",
  resetStrategy: "no_reset",
  inbounds: [],
  hosts: {},
  categoryId: "",
  isTrial: false,
});

const errorText = localizedApiError;

export const Plans: FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { getUserIsPending } = useGetUser();
  const modal = useDisclosure();
  const archiveDialog = useDisclosure();
  const cancelRef = useRef<HTMLButtonElement>(null);
  const [editing, setEditing] = useState<UserPlan | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<UserPlan | null>(null);
  const [draft, setDraft] = useState<PlanDraft>(emptyDraft());
  const [newCategoryName, setNewCategoryName] = useState("");
  const [usernames, setUsernames] = useState<Record<number, string>>({});
  const account = useQuery<AccountSummary, Error>("account-summary", () => fetch("/account/summary"), { enabled: !getUserIsPending });
  const plans = useQuery<UserPlan[], Error>("user-plans", () => fetch("/user-plans"), { enabled: !getUserIsPending });
  const categories = useQuery<PlanCategory[], Error>("plan-categories", () => fetch("/plan-categories"), { enabled: !getUserIsPending });
  const networkOptions = useQuery<PlanNetworkOption[], Error>("plan-network-options", () => fetch("/plan-network-options"), { enabled: !getUserIsPending });
  const inboundOptions = networkOptions.data || [];
  const missingInbounds = networkOptions.isLoading
    ? []
    : missingPlanInboundTags(draft.inbounds, inboundOptions);
  const missingHosts = networkOptions.isLoading
    ? []
    : missingPlanHostIds(draft.hosts, inboundOptions);
  const canManage = account.data?.role === "OWNER" || account.data?.can_manage_plans;

  useEffect(() => {
    if (!modal.isOpen) return;
    setDraft(editing ? {
      name: editing.name,
      description: editing.description || "",
      dataGiB: String(editing.version.data_limit / GIB),
      durationDays: String(editing.version.duration_days),
      deviceLimit: editing.version.concurrent_user_limit === null ? "" : String(editing.version.concurrent_user_limit),
      resetStrategy: editing.version.reset_strategy,
      inbounds: normalizePlanInboundTags(editing.version.inbounds),
      hosts: normalizePlanHostScope(editing.version.hosts || {}),
      categoryId: editing.category_id === null ? "" : String(editing.category_id),
      isTrial: editing.is_trial,
    } : emptyDraft());
  }, [editing, modal.isOpen]);

  const save = useMutation(
    () => {
      const payload = {
        ...(editing ? {} : { name: draft.name.trim(), is_trial: draft.isTrial }),
        description: draft.description.trim() || null,
        category_id: draft.categoryId ? Number(draft.categoryId) : null,
        version: {
          data_limit: Math.round(Number(draft.dataGiB) * GIB),
          duration_days: Number(draft.durationDays),
          concurrent_user_limit: draft.deviceLimit ? Number(draft.deviceLimit) : null,
          reset_strategy: draft.resetStrategy,
          renewal_volume_strategy: "replace",
          renewal_time_strategy: "extend_max",
          inbounds: normalizePlanInboundTags(draft.inbounds),
          hosts: normalizePlanHostScope(draft.hosts),
        },
        allowed_admin_ids: [],
        include_subtree: false,
      };
      return fetch(editing ? `/user-plans/${editing.id}` : "/user-plans", { method: editing ? "PUT" : "POST", body: payload });
    },
    {
      onSuccess: () => { queryClient.invalidateQueries("user-plans"); modal.onClose(); toast({ title: "پلن ذخیره شد", status: "success", duration: 3000 }); },
      onError: (error) => { toast({ title: "ذخیره پلن انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
    }
  );

  const createCategory = useMutation(
    () => fetch("/plan-categories", {
      method: "POST",
      body: { name: newCategoryName.trim(), description: null },
    }),
    {
      onSuccess: () => {
        setNewCategoryName("");
        queryClient.invalidateQueries("plan-categories");
        toast({ title: "دسته‌بندی ساخته شد", status: "success", duration: 3000 });
      },
      onError: (error) => {
        toast({ title: "ساخت دسته‌بندی انجام نشد", description: errorText(error), status: "error", duration: 5000 });
      },
    }
  );

  const createUser = useMutation(
    ({ plan, username }: { plan: UserPlan; username: string }) => fetch("/users/from-plan", {
      method: "POST",
      body: { plan_id: plan.id, username, status: "active", idempotency_key: `create-${plan.id}-${crypto.randomUUID()}` },
    }),
    {
      onSuccess: (_, values) => { setUsernames((current) => ({ ...current, [values.plan.id]: "" })); queryClient.invalidateQueries("users"); queryClient.invalidateQueries("account-summary"); toast({ title: "کاربر از پلن ساخته شد", status: "success", duration: 3000 }); },
      onError: (error) => { toast({ title: "ساخت کاربر انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
    }
  );

  const archive = useMutation(
    (plan: UserPlan) => fetch(`/user-plans/${plan.id}`, { method: "DELETE" }),
    {
      onSuccess: () => { queryClient.invalidateQueries("user-plans"); archiveDialog.onClose(); toast({ title: "پلن بایگانی شد", status: "success", duration: 3000 }); },
      onError: (error) => { toast({ title: "بایگانی انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
    }
  );

  const openCreate = () => { setEditing(null); modal.onOpen(); };
  const openEdit = (plan: UserPlan) => { setEditing(plan); modal.onOpen(); };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!draft.categoryId) {
      toast({ title: "دسته‌بندی پلن را انتخاب کنید", status: "warning", duration: 3000 });
      return;
    }
    if (networkOptions.isLoading) {
      toast({ title: "فهرست Inboundها هنوز در حال دریافت است", status: "warning", duration: 3000 });
      return;
    }
    if (draft.inbounds.length === 0) {
      toast({ title: "حداقل یک Inbound انتخاب کنید", status: "warning", duration: 3000 });
      return;
    }
    if (missingInbounds.length > 0) {
      toast({
        title: "Inbound قدیمی را تعیین تکلیف کنید",
        description: "Tag حذف‌شده را از انتخاب خارج کنید یا ابتدا آن را در تنظیمات Xray برگردانید.",
        status: "warning",
        duration: 5000,
      });
      return;
    }
    if (missingHosts.length > 0) {
      toast({
        title: "Host حذف‌شده یا غیرفعال را تعیین تکلیف کنید",
        description: `Host ID: ${missingHosts.join(", ")}`,
        status: "warning",
        duration: 5000,
      });
      return;
    }
    if (draft.inbounds.some((tag) => !(draft.hosts[tag] || []).length)) {
      toast({ title: "برای هر Inbound حداقل یک Host فعال انتخاب کنید", status: "warning", duration: 4000 });
      return;
    }
    save.mutate();
  };

  return (
    <AppShell>
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} gap={4} mb={6}>
        <Box><Text color="primary.300" fontSize="xs" fontWeight="800">اشتراک استاندارد</Text><Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={1}>پلن‌های کاربر</Text><Text color="gray.300" mt={1}>نسخه‌های تغییرناپذیر، دسترسی شاخه‌ای و ساخت کاربر بدون ورود دستی محدودیت‌ها.</Text></Box>
        {canManage && <Button minH="44px" colorScheme="primary" color="#07130e" onClick={openCreate} isDisabled={(categories.data || []).length === 0}>پلن جدید</Button>}
      </Stack>
      {canManage && (
        <Card p={5} mb={5} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="18px">
          <Text fontWeight="800">دسته‌بندی پلن‌ها</Text>
          <Text color="gray.400" fontSize="sm" mt={1}>پلن را اینجا دسته‌بندی کنید؛ دسترسی هر ادمین به دسته‌ها فقط از صفحه ادمین‌ها تنظیم می‌شود.</Text>
          <HStack mt={4} align="end" flexWrap="wrap">
            <FormControl maxW={{ base: "full", md: "360px" }}>
              <FormLabel fontSize="sm">نام دسته‌بندی جدید</FormLabel>
              <Input value={newCategoryName} onChange={(event) => setNewCategoryName(event.target.value)} maxLength={128} />
            </FormControl>
            <Button minH="40px" isDisabled={!newCategoryName.trim()} isLoading={createCategory.isLoading} onClick={() => createCategory.mutate()}>افزودن دسته</Button>
          </HStack>
          <HStack mt={4} spacing={2} flexWrap="wrap">
            {(categories.data || []).map((category) => <Badge key={category.id} colorScheme="purple" px={3} py={1.5}>{category.name} · {category.plan_count}</Badge>)}
            {!categories.isLoading && (categories.data || []).length === 0 && <Text color="gray.400" fontSize="sm">ابتدا یک دسته‌بندی بسازید.</Text>}
          </HStack>
        </Card>
      )}
      {categories.isError && <Alert status="error" mb={4}><AlertIcon />دسته‌بندی‌ها دریافت نشدند.</Alert>}
      {plans.isError && <Alert status="error" mb={4}><AlertIcon />پلن‌ها دریافت نشدند.</Alert>}
      {plans.isLoading ? <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>{[1, 2, 3].map((value) => <Skeleton key={value} h="245px" borderRadius="18px" />)}</SimpleGrid> : (
        <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>
          {(plans.data || []).map((plan) => (
            <Card key={plan.id} p={4} bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border)" borderRadius="14px" boxShadow="panel">
              <HStack justify="space-between" align="start"><Box minW={0}><Text as="h2" fontSize="lg" fontWeight="800" overflowWrap="anywhere">{plan.name}</Text><Text color="gray.400" fontSize="sm" mt={1}>{plan.description || "بدون توضیح"}</Text></Box><Stack align="end" spacing={1}>{plan.is_trial && <Badge colorScheme="orange">آزمایشی</Badge>}<Badge colorScheme="cyan">نسخه {plan.version_number}</Badge><Badge colorScheme="purple">{plan.category_name || "بدون دسته"}</Badge></Stack></HStack>
              <SimpleGrid columns={2} gap={3} mt={5}><Box><Text color="gray.400" fontSize="xs">حجم</Text><Text mt={1} fontWeight="700">{formatBytes(plan.version.data_limit)}</Text></Box><Box><Text color="gray.400" fontSize="xs">مدت</Text><Text mt={1} fontWeight="700">{plan.version.duration_days} روز</Text></Box><Box><Text color="gray.400" fontSize="xs">دستگاه</Text><Text mt={1}>{plan.version.concurrent_user_limit ?? "نامحدود"}</Text></Box><Box><Text color="gray.400" fontSize="xs">دسته‌بندی</Text><Text mt={1}>{plan.category_name || "بدون دسته"}</Text></Box></SimpleGrid>
              <FormControl mt={5}><FormLabel fontSize="xs">نام کاربری جدید</FormLabel><HStack><Input minH="44px" dir="ltr" value={usernames[plan.id] || ""} onChange={(event) => setUsernames((current) => ({ ...current, [plan.id]: event.target.value }))} /><Button minH="44px" isDisabled={!usernames[plan.id]?.trim()} isLoading={createUser.isLoading} onClick={() => createUser.mutate({ plan, username: usernames[plan.id].trim() })}>ساخت</Button></HStack></FormControl>
              {canManage && <HStack mt={4}><Button minH="44px" size="sm" variant="outline" onClick={() => openEdit(plan)}>نسخه جدید</Button><Button minH="44px" size="sm" variant="ghost" colorScheme="red" onClick={() => { setArchiveTarget(plan); archiveDialog.onOpen(); }}>بایگانی</Button></HStack>}
            </Card>
          ))}
        </SimpleGrid>
      )}
      {!plans.isLoading && !plans.isError && (plans.data || []).length === 0 && <Card p={8} bg="#111d17" borderWidth="1px" borderColor="#33483b" textAlign="center"><Text fontWeight="700">پلنی در دسترس نیست.</Text><Text color="gray.400" mt={2}>Owner یا مدیر مجاز باید نخستین پلن را بسازد.</Text></Card>}

      <Modal isOpen={modal.isOpen} onClose={modal.onClose} size="2xl" scrollBehavior="inside"><ModalOverlay bg="rgba(0,0,0,.72)" /><ModalContent as="form" onSubmit={submit} mx={3} my={3} maxH="calc(100dvh - 24px)" overflow="hidden" bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border-strong)"><ModalHeader ps={14}>{editing ? "ساخت نسخه جدید" : "پلن جدید"}</ModalHeader><ModalCloseButton top={3} insetInlineStart={3} insetInlineEnd="auto" /><ModalBody overflowY="auto"><Stack spacing={4}>
        <FormControl isRequired><FormLabel>نام پلن</FormLabel><Input minH="44px" value={draft.name} isReadOnly={Boolean(editing)} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} /></FormControl>
        <FormControl><FormLabel>توضیح</FormLabel><Textarea value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></FormControl>
        <FormControl isRequired><FormLabel>دسته‌بندی</FormLabel><Select value={draft.categoryId} onChange={(event) => setDraft((current) => ({ ...current, categoryId: event.target.value }))}><option value="">انتخاب دسته‌بندی</option>{(categories.data || []).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select><FormHelperText>اختصاص این دسته به ادمین‌ها از صفحه مدیریت ادمین انجام می‌شود.</FormHelperText></FormControl>
        {account.data?.role === "OWNER" && <FormControl><Checkbox minH="44px" alignItems="center" isChecked={draft.isTrial} isDisabled={Boolean(editing)} onChange={(event) => setDraft((current) => ({ ...current, isTrial: event.target.checked }))}>پلن آزمایشی</Checkbox><FormHelperText>مشخصات آزمایشی پس از ساخت تغییر نمی‌کند و هر ساخت موفق یک سهمیه تست مصرف می‌کند.</FormHelperText></FormControl>}
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}><FormControl isRequired><FormLabel>حجم (GiB)</FormLabel><Input minH="44px" type="number" min={0} step={0.01} dir="ltr" value={draft.dataGiB} onChange={(event) => setDraft((current) => ({ ...current, dataGiB: event.target.value }))} /></FormControl><FormControl isRequired><FormLabel>مدت (روز)</FormLabel><Input minH="44px" type="number" min={1} max={3650} dir="ltr" value={draft.durationDays} onChange={(event) => setDraft((current) => ({ ...current, durationDays: event.target.value }))} /></FormControl><FormControl><FormLabel>تعداد دستگاه</FormLabel><Input minH="44px" type="number" min={1} dir="ltr" value={draft.deviceLimit} onChange={(event) => setDraft((current) => ({ ...current, deviceLimit: event.target.value }))} /></FormControl><FormControl><FormLabel>ریست حجم</FormLabel><Select minH="44px" value={draft.resetStrategy} onChange={(event) => setDraft((current) => ({ ...current, resetStrategy: event.target.value as PlanDraft["resetStrategy"] }))}><option value="no_reset">بدون ریست</option><option value="day">روزانه</option><option value="week">هفتگی</option><option value="month">ماهانه</option><option value="year">سالانه</option></Select></FormControl></SimpleGrid>
        <FormControl>
          <FormLabel>Inboundها</FormLabel>
          <Stack maxH="280px" overflowY="auto" spacing={1} p={2} borderWidth="1px" borderColor="#33483b" borderRadius="10px">
            {networkOptions.isLoading && <Skeleton h="44px" borderRadius="8px" />}
            {inboundOptions.map((inbound) => (
              <Box key={inbound.tag} px={2} py={1} borderRadius="8px" bg={draft.inbounds.includes(inbound.tag) ? "whiteAlpha.50" : "transparent"}>
                <Checkbox
                  minH="44px"
                  colorScheme="primary"
                  isChecked={draft.inbounds.includes(inbound.tag)}
                  onChange={(event) => setDraft((current) => {
                    const inbounds = togglePlanInboundTag(current.inbounds, inbound.tag, event.target.checked);
                    const hosts = { ...current.hosts };
                    if (event.target.checked) hosts[inbound.tag] = hosts[inbound.tag] || [];
                    else delete hosts[inbound.tag];
                    return { ...current, inbounds, hosts: normalizePlanHostScope(hosts) };
                  })}
                >
                  <Stack spacing={0} dir="ltr">
                    <Text fontSize="sm" fontWeight="700" overflowWrap="anywhere">{inbound.tag}</Text>
                    <Text color="gray.400" fontSize="xs">
                      {inbound.protocol} · {inbound.network} · {inbound.tls || "none"}{inbound.port ? ` · ${inbound.port}` : ""}
                    </Text>
                  </Stack>
                </Checkbox>
                {draft.inbounds.includes(inbound.tag) && (
                  <Stack ms={7} mb={2} spacing={1}>
                    {inbound.hosts.map((host) => (
                      <Checkbox
                        key={host.id}
                        minH="44px"
                        colorScheme="cyan"
                        isChecked={(draft.hosts[inbound.tag] || []).includes(host.id)}
                        onChange={(event) => setDraft((current) => ({
                          ...current,
                          hosts: togglePlanHostId(current.hosts, inbound.tag, host.id, event.target.checked),
                        }))}
                      >
                        <Text fontSize="sm" overflowWrap="anywhere" dir="ltr">#{host.id} · {host.remark}</Text>
                      </Checkbox>
                    ))}
                    {(draft.hosts[inbound.tag] || [])
                      .filter((hostId) => !inbound.hosts.some((host) => host.id === hostId))
                      .map((hostId) => (
                        <Checkbox
                          key={hostId}
                          minH="44px"
                          colorScheme="red"
                          isChecked
                          onChange={(event) => setDraft((current) => ({
                            ...current,
                            hosts: togglePlanHostId(current.hosts, inbound.tag, hostId, event.target.checked),
                          }))}
                        >
                          <HStack dir="ltr"><Text fontSize="sm">#{hostId}</Text><Badge colorScheme="red">حذف‌شده / غیرفعال</Badge></HStack>
                        </Checkbox>
                      ))}
                    {inbound.hosts.length === 0 && (
                      <Text color="red.300" fontSize="xs">Host فعال و واجدشرایطی برای این Inbound وجود ندارد.</Text>
                    )}
                  </Stack>
                )}
              </Box>
            ))}
            {missingInbounds.map((tag) => (
              <Checkbox
                key={tag}
                minH="44px"
                px={2}
                colorScheme="red"
                isChecked
                onChange={(event) => setDraft((current) => ({
                  ...current,
                  inbounds: togglePlanInboundTag(current.inbounds, tag, event.target.checked),
                  hosts: Object.fromEntries(Object.entries(current.hosts).filter(([key]) => key !== tag)),
                }))}
              >
                <HStack dir="ltr">
                  <Text fontSize="sm" overflowWrap="anywhere">{tag}</Text>
                  <Badge colorScheme="red">حذف‌شده / قدیمی</Badge>
                </HStack>
              </Checkbox>
            ))}
            {inboundOptions.length === 0 && missingInbounds.length === 0 && (
              <Text color="gray.400" fontSize="sm" p={2}>Inbound تنظیم‌شده‌ای پیدا نشد.</Text>
            )}
          </Stack>
          <FormHelperText>حداقل یک Inbound و برای هر Inbound حداقل یک Host فعال باید صریح انتخاب شود. انتخاب خالی هرگز به معنی همه نیست.</FormHelperText>
        </FormControl>
      </Stack></ModalBody><ModalFooter flexShrink={0} gap={2} px={{ base: 3, md: 6 }} py={3} borderTopWidth="1px" borderColor="var(--panel-border)"><Button minH="42px" variant="ghost" onClick={modal.onClose}>انصراف</Button><Button minH="42px" type="submit" colorScheme="primary" color="#07130e" isLoading={save.isLoading}>ذخیره</Button></ModalFooter></ModalContent></Modal>

      <AlertDialog isOpen={archiveDialog.isOpen} leastDestructiveRef={cancelRef} onClose={archiveDialog.onClose}><AlertDialogOverlay><AlertDialogContent bg="#111d17" color="gray.100"><AlertDialogHeader>بایگانی پلن</AlertDialogHeader><AlertDialogBody>پلن «{archiveTarget?.name}» برای ساخت و تمدید جدید غیرفعال می‌شود.</AlertDialogBody><AlertDialogFooter gap={3}><Button ref={cancelRef} onClick={archiveDialog.onClose}>انصراف</Button><Button colorScheme="red" isLoading={archive.isLoading} onClick={() => archiveTarget && archive.mutate(archiveTarget)}>بایگانی</Button></AlertDialogFooter></AlertDialogContent></AlertDialogOverlay></AlertDialog>
    </AppShell>
  );
};

export default Plans;
