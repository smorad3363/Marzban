import {
  Alert, AlertIcon, Badge, Box, Button, Checkbox, FormControl, FormHelperText,
  FormLabel, HStack, Input, Modal, ModalBody, ModalCloseButton, ModalContent,
  ModalFooter, ModalHeader, ModalOverlay, Select, SimpleGrid, Skeleton, Stack,
  Text, Textarea, useToast,
} from "@chakra-ui/react";
import { FC, FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { PlanCategory, PlanNetworkOption } from "types/Admin";
import { localizedApiError } from "utils/apiError";
import {
  missingPlanHostIds, missingPlanInboundTags, normalizePlanHostScope,
  normalizePlanInboundTags, togglePlanHostId, togglePlanInboundTag,
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
  name: "", description: "", dataGiB: "10", durationDays: "30",
  deviceLimit: "", resetStrategy: "no_reset", inbounds: [], hosts: {},
  categoryId: "", isTrial: false,
});

type Props = {
  isOpen: boolean;
  isOwner: boolean;
  onClose: () => void;
};

export const PlanCreateModal: FC<Props> = ({ isOpen, isOwner, onClose }) => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<PlanDraft>(emptyDraft());
  const categories = useQuery<PlanCategory[], Error>("plan-categories", () => fetch("/plan-categories"), { enabled: isOpen });
  const networkOptions = useQuery<PlanNetworkOption[], Error>("plan-network-options", () => fetch("/plan-network-options"), { enabled: isOpen });
  const inboundOptions = networkOptions.data || [];
  const missingInbounds = networkOptions.isLoading ? [] : missingPlanInboundTags(draft.inbounds, inboundOptions);
  const missingHosts = networkOptions.isLoading ? [] : missingPlanHostIds(draft.hosts, inboundOptions);

  useEffect(() => {
    if (isOpen) setDraft(emptyDraft());
  }, [isOpen]);

  const save = useMutation(
    () => fetch("/user-plans", {
      method: "POST",
      body: {
        name: draft.name.trim(),
        description: draft.description.trim() || null,
        category_id: Number(draft.categoryId),
        is_trial: draft.isTrial,
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
      },
    }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("user-plans");
        onClose();
        toast({ title: "پلن ذخیره شد", status: "success", duration: 3000 });
      },
      onError: (error) => { toast({ title: "ذخیره پلن انجام نشد", description: localizedApiError(error), status: "error", duration: 5000 }); },
    }
  );

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
      toast({ title: "Inbound قدیمی را تعیین تکلیف کنید", description: "Tag حذف‌شده را از انتخاب خارج کنید یا ابتدا آن را در تنظیمات Xray برگردانید.", status: "warning", duration: 5000 });
      return;
    }
    if (missingHosts.length > 0) {
      toast({ title: "Host حذف‌شده یا غیرفعال را تعیین تکلیف کنید", description: `Host ID: ${missingHosts.join(", ")}`, status: "warning", duration: 5000 });
      return;
    }
    if (draft.inbounds.some((tag) => !(draft.hosts[tag] || []).length)) {
      toast({ title: "برای هر Inbound حداقل یک Host فعال انتخاب کنید", status: "warning", duration: 4000 });
      return;
    }
    save.mutate();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} size="2xl" scrollBehavior="inside">
      <ModalOverlay bg="rgba(0,0,0,.72)" />
      <ModalContent as="form" onSubmit={submit} mx={3} my={3} maxH="calc(100dvh - 24px)" overflow="hidden" bg="var(--panel-surface)" color="gray.100" borderWidth="1px" borderColor="var(--panel-border-strong)">
        <ModalHeader ps={14}>ساخت پلن</ModalHeader>
        <ModalCloseButton top={3} insetInlineStart={3} insetInlineEnd="auto" />
        <ModalBody overflowY="auto">
          <Stack spacing={4}>
            {categories.isError && <Alert status="error"><AlertIcon />دسته‌بندی‌ها دریافت نشدند.</Alert>}
            {!categories.isLoading && !categories.isError && (categories.data || []).length === 0 && <Alert status="warning"><AlertIcon />ابتدا از صفحه پلن‌ها یک دسته‌بندی بسازید.</Alert>}
            <FormControl isRequired><FormLabel>نام پلن</FormLabel><Input minH="44px" value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} /></FormControl>
            <FormControl><FormLabel>توضیح</FormLabel><Textarea value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} /></FormControl>
            <FormControl isRequired><FormLabel>دسته‌بندی</FormLabel><Select value={draft.categoryId} onChange={(event) => setDraft((current) => ({ ...current, categoryId: event.target.value }))}><option value="">انتخاب دسته‌بندی</option>{(categories.data || []).map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select><FormHelperText>اختصاص این دسته به ادمین‌ها از صفحه مدیریت ادمین انجام می‌شود.</FormHelperText></FormControl>
            {isOwner && <FormControl><Checkbox minH="44px" alignItems="center" isChecked={draft.isTrial} onChange={(event) => setDraft((current) => ({ ...current, isTrial: event.target.checked }))}>پلن آزمایشی</Checkbox><FormHelperText>هر ساخت موفق از این پلن یک سهمیه تست مصرف می‌کند.</FormHelperText></FormControl>}
            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <FormControl isRequired><FormLabel>حجم (GiB)</FormLabel><Input minH="44px" type="number" min={0} step={0.01} dir="ltr" value={draft.dataGiB} onChange={(event) => setDraft((current) => ({ ...current, dataGiB: event.target.value }))} /></FormControl>
              <FormControl isRequired><FormLabel>مدت (روز)</FormLabel><Input minH="44px" type="number" min={1} max={3650} dir="ltr" value={draft.durationDays} onChange={(event) => setDraft((current) => ({ ...current, durationDays: event.target.value }))} /></FormControl>
              <FormControl><FormLabel>تعداد دستگاه</FormLabel><Input minH="44px" type="number" min={1} dir="ltr" value={draft.deviceLimit} onChange={(event) => setDraft((current) => ({ ...current, deviceLimit: event.target.value }))} /></FormControl>
              <FormControl><FormLabel>ریست حجم</FormLabel><Select minH="44px" value={draft.resetStrategy} onChange={(event) => setDraft((current) => ({ ...current, resetStrategy: event.target.value as PlanDraft["resetStrategy"] }))}><option value="no_reset">بدون ریست</option><option value="day">روزانه</option><option value="week">هفتگی</option><option value="month">ماهانه</option><option value="year">سالانه</option></Select></FormControl>
            </SimpleGrid>
            <FormControl>
              <FormLabel>Inboundها</FormLabel>
              <Stack maxH="280px" overflowY="auto" spacing={1} p={2} borderWidth="1px" borderColor="var(--panel-border)" borderRadius="10px">
                {networkOptions.isLoading && <Skeleton h="44px" borderRadius="8px" />}
                {inboundOptions.map((inbound) => (
                  <Box key={inbound.tag} px={2} py={1} borderRadius="8px" bg={draft.inbounds.includes(inbound.tag) ? "whiteAlpha.50" : "transparent"}>
                    <Checkbox minH="44px" colorScheme="primary" isChecked={draft.inbounds.includes(inbound.tag)} onChange={(event) => setDraft((current) => {
                      const inbounds = togglePlanInboundTag(current.inbounds, inbound.tag, event.target.checked);
                      const hosts = { ...current.hosts };
                      if (event.target.checked) hosts[inbound.tag] = hosts[inbound.tag] || [];
                      else delete hosts[inbound.tag];
                      return { ...current, inbounds, hosts: normalizePlanHostScope(hosts) };
                    })}>
                      <Stack spacing={0} dir="ltr"><Text fontSize="sm" fontWeight="700" overflowWrap="anywhere">{inbound.tag}</Text><Text color="gray.400" fontSize="xs">{inbound.protocol} · {inbound.network} · {inbound.tls || "none"}{inbound.port ? ` · ${inbound.port}` : ""}</Text></Stack>
                    </Checkbox>
                    {draft.inbounds.includes(inbound.tag) && <Stack ms={7} mb={2} spacing={1}>
                      {inbound.hosts.map((host) => <Checkbox key={host.id} minH="44px" colorScheme="cyan" isChecked={(draft.hosts[inbound.tag] || []).includes(host.id)} onChange={(event) => setDraft((current) => ({ ...current, hosts: togglePlanHostId(current.hosts, inbound.tag, host.id, event.target.checked) }))}><Text fontSize="sm" overflowWrap="anywhere" dir="ltr">#{host.id} · {host.remark}</Text></Checkbox>)}
                      {inbound.hosts.length === 0 && <Text color="red.300" fontSize="xs">Host فعال و واجدشرایطی برای این Inbound وجود ندارد.</Text>}
                    </Stack>}
                  </Box>
                ))}
                {missingInbounds.map((tag) => <Checkbox key={tag} minH="44px" px={2} colorScheme="red" isChecked onChange={(event) => setDraft((current) => ({ ...current, inbounds: togglePlanInboundTag(current.inbounds, tag, event.target.checked), hosts: Object.fromEntries(Object.entries(current.hosts).filter(([key]) => key !== tag)) }))}><HStack dir="ltr"><Text fontSize="sm">{tag}</Text><Badge colorScheme="red">حذف‌شده / قدیمی</Badge></HStack></Checkbox>)}
                {inboundOptions.length === 0 && missingInbounds.length === 0 && !networkOptions.isLoading && <Text color="gray.400" fontSize="sm" p={2}>Inbound تنظیم‌شده‌ای پیدا نشد.</Text>}
              </Stack>
              <FormHelperText>حداقل یک Inbound و برای هر Inbound حداقل یک Host فعال باید صریح انتخاب شود.</FormHelperText>
            </FormControl>
          </Stack>
        </ModalBody>
        <ModalFooter flexShrink={0} gap={2} px={{ base: 3, md: 6 }} py={3} borderTopWidth="1px" borderColor="var(--panel-border)"><Button minH="42px" variant="ghost" onClick={onClose}>انصراف</Button><Button minH="42px" type="submit" colorScheme="primary" color="#07130e" isLoading={save.isLoading} isDisabled={(categories.data || []).length === 0}>ذخیره</Button></ModalFooter>
      </ModalContent>
    </Modal>
  );
};
