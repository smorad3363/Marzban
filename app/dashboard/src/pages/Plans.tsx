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
import { AccountSummary, UserPlan } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const GIB = 1024 ** 3;

type PlanDraft = {
  name: string;
  description: string;
  dataGiB: string;
  durationDays: string;
  deviceLimit: string;
  resetStrategy: "no_reset" | "day" | "week" | "month" | "year";
  inbounds: string;
  allowedAdminIds: string;
  includeSubtree: boolean;
};

const emptyDraft = (): PlanDraft => ({
  name: "",
  description: "",
  dataGiB: "10",
  durationDays: "30",
  deviceLimit: "",
  resetStrategy: "no_reset",
  inbounds: "",
  allowedAdminIds: "",
  includeSubtree: false,
});

const errorText = (error: any) => {
  const detail = error?.data?.detail || error?.response?._data?.detail || error?.message;
  return typeof detail === "object" ? detail.message || detail.code : detail;
};

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
  const [usernames, setUsernames] = useState<Record<number, string>>({});

  const account = useQuery<AccountSummary, Error>("account-summary", () => fetch("/account/summary"), { enabled: !getUserIsPending });
  const plans = useQuery<UserPlan[], Error>("user-plans", () => fetch("/user-plans"), { enabled: !getUserIsPending });
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
      inbounds: editing.version.inbounds.join(", "),
      allowedAdminIds: editing.allowed_admin_ids.join(", "),
      includeSubtree: editing.include_subtree,
    } : emptyDraft());
  }, [editing, modal.isOpen]);

  const save = useMutation(
    () => {
      const payload = {
        ...(editing ? {} : { name: draft.name.trim() }),
        description: draft.description.trim() || null,
        version: {
          data_limit: Math.round(Number(draft.dataGiB) * GIB),
          duration_days: Number(draft.durationDays),
          concurrent_user_limit: draft.deviceLimit ? Number(draft.deviceLimit) : null,
          reset_strategy: draft.resetStrategy,
          renewal_volume_strategy: "replace",
          renewal_time_strategy: "extend_max",
          inbounds: draft.inbounds.split(",").map((value) => value.trim()).filter(Boolean),
        },
        allowed_admin_ids: draft.allowedAdminIds.split(",").map((value) => Number(value.trim())).filter((value) => Number.isInteger(value) && value > 0),
        include_subtree: draft.includeSubtree,
      };
      return fetch(editing ? `/user-plans/${editing.id}` : "/user-plans", { method: editing ? "PUT" : "POST", body: payload });
    },
    {
      onSuccess: () => { queryClient.invalidateQueries("user-plans"); modal.onClose(); toast({ title: "پلن ذخیره شد", status: "success", duration: 3000 }); },
      onError: (error) => { toast({ title: "ذخیره پلن انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
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
  const submit = (event: FormEvent) => { event.preventDefault(); save.mutate(); };

  return (
    <AppShell>
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} gap={4} mb={6}>
        <Box><Text color="primary.300" fontSize="xs" fontWeight="800">اشتراک استاندارد</Text><Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" mt={1}>پلن‌های کاربر</Text><Text color="gray.300" mt={1}>نسخه‌های تغییرناپذیر، دسترسی شاخه‌ای و ساخت کاربر بدون ورود دستی محدودیت‌ها.</Text></Box>
        {canManage && <Button minH="44px" colorScheme="primary" color="#07130e" onClick={openCreate}>پلن جدید</Button>}
      </Stack>
      {plans.isError && <Alert status="error" mb={4}><AlertIcon />پلن‌ها دریافت نشدند.</Alert>}
      {plans.isLoading ? <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>{[1, 2, 3].map((value) => <Skeleton key={value} h="245px" borderRadius="18px" />)}</SimpleGrid> : (
        <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>
          {(plans.data || []).map((plan) => (
            <Card key={plan.id} p={5} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="18px" boxShadow="panel">
              <HStack justify="space-between" align="start"><Box minW={0}><Text as="h2" fontSize="lg" fontWeight="800" overflowWrap="anywhere">{plan.name}</Text><Text color="gray.400" fontSize="sm" mt={1}>{plan.description || "بدون توضیح"}</Text></Box><Badge colorScheme="cyan">v{plan.version_number}</Badge></HStack>
              <SimpleGrid columns={2} gap={3} mt={5}><Box><Text color="gray.400" fontSize="xs">حجم</Text><Text mt={1} fontWeight="700">{formatBytes(plan.version.data_limit)}</Text></Box><Box><Text color="gray.400" fontSize="xs">مدت</Text><Text mt={1} fontWeight="700">{plan.version.duration_days} روز</Text></Box><Box><Text color="gray.400" fontSize="xs">دستگاه</Text><Text mt={1}>{plan.version.concurrent_user_limit ?? "نامحدود"}</Text></Box><Box><Text color="gray.400" fontSize="xs">دسترسی</Text><Text mt={1}>{plan.include_subtree ? "کل زیرشاخه" : `${plan.allowed_admin_ids.length} ادمین`}</Text></Box></SimpleGrid>
              <FormControl mt={5}><FormLabel fontSize="xs">نام کاربری جدید</FormLabel><HStack><Input minH="44px" dir="ltr" value={usernames[plan.id] || ""} onChange={(event) => setUsernames((current) => ({ ...current, [plan.id]: event.target.value }))} /><Button minH="44px" isDisabled={!usernames[plan.id]?.trim()} isLoading={createUser.isLoading} onClick={() => createUser.mutate({ plan, username: usernames[plan.id].trim() })}>ساخت</Button></HStack></FormControl>
              {canManage && <HStack mt={4}><Button minH="44px" size="sm" variant="outline" onClick={() => openEdit(plan)}>نسخه جدید</Button><Button minH="44px" size="sm" variant="ghost" colorScheme="red" onClick={() => { setArchiveTarget(plan); archiveDialog.onOpen(); }}>بایگانی</Button></HStack>}
            </Card>
          ))}
        </SimpleGrid>
      )}
      {!plans.isLoading && !plans.isError && (plans.data || []).length === 0 && <Card p={8} bg="#111d17" borderWidth="1px" borderColor="#33483b" textAlign="center"><Text fontWeight="700">پلنی در دسترس نیست.</Text><Text color="gray.400" mt={2}>Owner یا مدیر مجاز باید نخستین پلن را بسازد.</Text></Card>}

      <Modal isOpen={modal.isOpen} onClose={modal.onClose} size="2xl" scrollBehavior="inside"><ModalOverlay bg="rgba(0,0,0,.72)" /><ModalContent as="form" onSubmit={submit} mx={3} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b"><ModalHeader>{editing ? "ساخت نسخه جدید" : "پلن جدید"}</ModalHeader><ModalCloseButton /><ModalBody><Stack spacing={4}>
        <FormControl isRequired><FormLabel>نام پلن</FormLabel><Input minH="44px" value={draft.name} isReadOnly={Boolean(editing)} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} /></FormControl>
        <FormControl><FormLabel>توضیح</FormLabel><Textarea value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></FormControl>
        <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}><FormControl isRequired><FormLabel>حجم (GiB)</FormLabel><Input minH="44px" type="number" min={0} step={0.01} dir="ltr" value={draft.dataGiB} onChange={(event) => setDraft((current) => ({ ...current, dataGiB: event.target.value }))} /></FormControl><FormControl isRequired><FormLabel>مدت (روز)</FormLabel><Input minH="44px" type="number" min={1} max={3650} dir="ltr" value={draft.durationDays} onChange={(event) => setDraft((current) => ({ ...current, durationDays: event.target.value }))} /></FormControl><FormControl><FormLabel>تعداد دستگاه</FormLabel><Input minH="44px" type="number" min={1} dir="ltr" value={draft.deviceLimit} onChange={(event) => setDraft((current) => ({ ...current, deviceLimit: event.target.value }))} /></FormControl><FormControl><FormLabel>ریست حجم</FormLabel><Select minH="44px" value={draft.resetStrategy} onChange={(event) => setDraft((current) => ({ ...current, resetStrategy: event.target.value as PlanDraft["resetStrategy"] }))}><option value="no_reset">بدون ریست</option><option value="day">روزانه</option><option value="week">هفتگی</option><option value="month">ماهانه</option><option value="year">سالانه</option></Select></FormControl></SimpleGrid>
        <FormControl><FormLabel>Inboundها</FormLabel><Input minH="44px" dir="ltr" value={draft.inbounds} onChange={(event) => setDraft((current) => ({ ...current, inbounds: event.target.value }))} /><FormHelperText>Tagها را با ویرگول جدا کنید.</FormHelperText></FormControl>
        <FormControl><FormLabel>شناسه ادمین‌های مجاز</FormLabel><Input minH="44px" dir="ltr" value={draft.allowedAdminIds} onChange={(event) => setDraft((current) => ({ ...current, allowedAdminIds: event.target.value }))} /><FormHelperText>IDها را با ویرگول جدا کنید؛ Owner همیشه دسترسی دارد.</FormHelperText></FormControl>
        <Checkbox minH="44px" colorScheme="primary" isChecked={draft.includeSubtree} onChange={(event) => setDraft((current) => ({ ...current, includeSubtree: event.target.checked }))}>دسترسی به زیرشاخه ادمین‌های انتخاب‌شده هم منتشر شود</Checkbox>
      </Stack></ModalBody><ModalFooter gap={3}><Button minH="44px" variant="ghost" onClick={modal.onClose}>انصراف</Button><Button minH="44px" type="submit" colorScheme="primary" color="#07130e" isLoading={save.isLoading}>ذخیره</Button></ModalFooter></ModalContent></Modal>

      <AlertDialog isOpen={archiveDialog.isOpen} leastDestructiveRef={cancelRef} onClose={archiveDialog.onClose}><AlertDialogOverlay><AlertDialogContent bg="#111d17" color="gray.100"><AlertDialogHeader>بایگانی پلن</AlertDialogHeader><AlertDialogBody>پلن «{archiveTarget?.name}» برای ساخت و تمدید جدید غیرفعال می‌شود.</AlertDialogBody><AlertDialogFooter gap={3}><Button ref={cancelRef} onClick={archiveDialog.onClose}>انصراف</Button><Button colorScheme="red" isLoading={archive.isLoading} onClick={() => archiveTarget && archive.mutate(archiveTarget)}>بایگانی</Button></AlertDialogFooter></AlertDialogContent></AlertDialogOverlay></AlertDialog>
    </AppShell>
  );
};

export default Plans;
