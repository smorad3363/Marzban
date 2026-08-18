import {
  Alert,
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
  Input,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
  Switch,
  Text,
  VStack,
  chakra,
  useToast,
} from "@chakra-ui/react";
import {
  AdjustmentsHorizontalIcon,
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { AppShell } from "components/AppShell";
import useGetUser from "hooks/useGetUser";
import { FC, FormEvent, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import {
  DeviceLimitIncidentList,
  DeviceLimitPenaltyStage,
  DeviceLimitSettings,
  PenaltyAction,
} from "types/DeviceLimit";

const LimitIcon = chakra(ShieldCheckIcon, { baseStyle: { w: 5, h: 5 } });
const TuneIcon = chakra(AdjustmentsHorizontalIcon, { baseStyle: { w: 5, h: 5 } });
const WarningIcon = chakra(ExclamationTriangleIcon, { baseStyle: { w: 5, h: 5 } });
const RefreshIcon = chakra(ArrowPathIcon, { baseStyle: { w: 4, h: 4 } });
const PAGE_SIZE = 20;
const riskKey = (value: number) => value >= 80 ? "high" : value >= 50 ? "medium" : "low";

const secondsToMinutes = (seconds: number | null) =>
  seconds === null ? "" : String(Math.round(seconds / 60));

const SettingsSection: FC<{
  settings: DeviceLimitSettings;
  stages: DeviceLimitPenaltyStage[];
}> = ({ settings, stages }) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(settings);
  const [stageForm, setStageForm] = useState(stages);

  useEffect(() => setForm(settings), [settings]);
  useEffect(() => setStageForm(stages), [stages]);

  const saveSettings = useMutation(
    () => fetch<DeviceLimitSettings>("/device-limit/settings", { method: "PUT", body: form }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("device-limit-settings");
        toast({ title: t("deviceLimit.settingsSaved"), status: "success", duration: 3000 });
      },
      onError: (error: any) => {
        toast({
          title: t("deviceLimit.saveFailed"),
          description: error?.data?.detail || error?.message,
          status: "error",
          duration: 5000,
        });
      },
    }
  );

  const saveStages = useMutation(
    () => fetch("/device-limit/penalty-stages", {
      method: "PUT",
      body: { stages: stageForm.map(({ id, ...stage }) => stage) },
    }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("device-limit-stages");
        toast({ title: t("deviceLimit.penaltiesSaved"), status: "success", duration: 3000 });
      },
      onError: (error: any) => {
        toast({
          title: t("deviceLimit.saveFailed"),
          description: error?.data?.detail || error?.message,
          status: "error",
          duration: 5000,
        });
      },
    }
  );

  const numberField = (key: keyof DeviceLimitSettings, value: string) =>
    setForm((current) => ({ ...current, [key]: Number(value) }));

  const updateStage = <K extends keyof DeviceLimitPenaltyStage>(
    index: number,
    key: K,
    value: DeviceLimitPenaltyStage[K]
  ) => setStageForm((current) => current.map((stage, itemIndex) =>
    itemIndex === index ? { ...stage, [key]: value } : stage
  ));

  const submitSettings = (event: FormEvent) => {
    event.preventDefault();
    saveSettings.mutate();
  };

  return (
    <Stack spacing={5}>
      <Card
        as="form"
        onSubmit={submitSettings}
        bg="linear-gradient(145deg, rgba(14,25,20,.98), rgba(7,19,23,.98))"
        color="gray.100"
        borderWidth="1px"
        borderColor="#345346"
        borderRadius={{ base: "16px", md: "20px" }}
        boxShadow="panel"
        overflow="hidden"
      >
        <HStack p={{ base: 4, md: 5 }} borderBottomWidth="1px" borderColor="#2b4437" align="start">
          <Box p={2.5} borderRadius="11px" bg="rgba(34,197,94,.1)" color="green.200"><TuneIcon /></Box>
          <Box minW={0}>
            <Text fontWeight="800">{t("deviceLimit.runtimeSettings")}</Text>
            <Text color="gray.400" fontSize="sm" mt={1}>{t("deviceLimit.runtimeSettingsHelp")}</Text>
          </Box>
          <Switch
            ms="auto"
            flexShrink={0}
            colorScheme="primary"
            size="lg"
            isChecked={form.enabled}
            onChange={(event) => setForm((current) => ({ ...current, enabled: event.target.checked }))}
            aria-label={t("deviceLimit.enabled")}
          />
        </HStack>

        <Box p={{ base: 4, md: 5 }}>
          <Text fontWeight="800" mb={3}>{t("deviceLimit.capabilities")}</Text>
          <SimpleGrid columns={{ base: 1, md: 3 }} gap={3} mb={5}>
            {([
              ["device_slots_enabled", "deviceLimit.capabilitySlots", "deviceLimit.capabilitySlotsHelp"],
              ["ip_detection_enabled", "deviceLimit.capabilityIp", "deviceLimit.capabilityIpHelp"],
              ["client_fingerprint_enabled", "deviceLimit.capabilityClient", "deviceLimit.capabilityClientHelp"],
            ] as const).map(([key, label, help]) => (
              <FormControl key={key} p={3} borderWidth="1px" borderColor={form[key] ? "rgba(34,197,94,.48)" : "#33483b"} borderRadius="10px" bg={form[key] ? "rgba(34,197,94,.06)" : "transparent"}>
                <Checkbox colorScheme="primary" isChecked={form[key]} onChange={(event) => setForm((current) => ({ ...current, [key]: event.target.checked }))}>
                  {t(label)}
                </Checkbox>
                <FormHelperText color="gray.400">{t(help)}</FormHelperText>
              </FormControl>
            ))}
          </SimpleGrid>
          <Text fontWeight="800" mb={3}>{t("deviceLimit.detectionTiming")}</Text>
          <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={5}>
            <FormControl isDisabled={!form.ip_detection_enabled}>
              <FormLabel>{t("deviceLimit.checkInterval")}</FormLabel>
              <Input dir="ltr" type="number" min={10} max={3600} value={form.check_interval_seconds} onChange={(event) => numberField("check_interval_seconds", event.target.value)} />
            </FormControl>
            <FormControl isDisabled={!form.ip_detection_enabled}>
              <FormLabel>{t("deviceLimit.activeWindow")}</FormLabel>
              <Input dir="ltr" type="number" min={30} max={86400} value={form.active_window_seconds} onChange={(event) => numberField("active_window_seconds", event.target.value)} />
            </FormControl>
            <FormControl isDisabled={!form.ip_detection_enabled}>
              <FormLabel>{t("deviceLimit.hitThreshold")}</FormLabel>
              <Input dir="ltr" type="number" min={1} max={100} value={form.min_successful_connections} onChange={(event) => numberField("min_successful_connections", event.target.value)} />
              <FormHelperText color="gray.400">{t("deviceLimit.hitThresholdHelp")}</FormHelperText>
            </FormControl>
            <FormControl isDisabled={!form.ip_detection_enabled}>
              <FormLabel>{t("deviceLimit.handoffGrace")}</FormLabel>
              <Input dir="ltr" type="number" min={0} max={600} value={form.handoff_grace_seconds} onChange={(event) => numberField("handoff_grace_seconds", event.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>{t("deviceLimit.strikeResetDays")}</FormLabel>
              <Input dir="ltr" type="number" min={1} value={Math.round(form.strike_reset_seconds / 86400)} onChange={(event) => setForm((current) => ({ ...current, strike_reset_seconds: Number(event.target.value) * 86400 }))} />
            </FormControl>
            <FormControl>
              <FormLabel>{t("deviceLimit.fullIpRetention")}</FormLabel>
              <Input dir="ltr" type="number" min={1} max={30} value={form.full_ip_retention_days} onChange={(event) => numberField("full_ip_retention_days", event.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>{t("deviceLimit.incidentRetention")}</FormLabel>
              <Input dir="ltr" type="number" min={7} max={3650} value={form.incident_retention_days} onChange={(event) => numberField("incident_retention_days", event.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>{t("deviceLimit.auditRetention")}</FormLabel>
              <Input dir="ltr" type="number" min={30} max={3650} value={form.audit_retention_days} onChange={(event) => numberField("audit_retention_days", event.target.value)} />
            </FormControl>
            <FormControl>
              <FormLabel>{t("deviceLimit.warningCleanupHours")}</FormLabel>
              <Input dir="ltr" type="number" min={0} max={8760} value={Math.round(form.warning_auto_delete_seconds / 3600)} onChange={(event) => setForm((current) => ({ ...current, warning_auto_delete_seconds: Number(event.target.value) * 3600 }))} />
              <FormHelperText color="gray.400">{t("deviceLimit.zeroDisabled")}</FormHelperText>
            </FormControl>
            <FormControl p={3} borderWidth="1px" borderColor={form.auto_delete_enabled ? "rgba(239,68,68,.48)" : "#33483b"} borderRadius="10px">
              <Checkbox colorScheme="red" isChecked={form.auto_delete_enabled} onChange={(event) => setForm((current) => ({ ...current, auto_delete_enabled: event.target.checked }))}>
                {t("deviceLimit.autoDelete")}
              </Checkbox>
              <FormHelperText color="gray.400">{t("deviceLimit.autoDeleteHelp")}</FormHelperText>
            </FormControl>
          </SimpleGrid>
          <HStack mt={5} justify="end">
            <Button type="submit" minH="44px" colorScheme="primary" color="#07130e" isLoading={saveSettings.isLoading}>{t("save")}</Button>
          </HStack>
        </Box>
      </Card>

      <Card bg="#0e1914" color="gray.100" borderWidth="1px" borderColor="#345346" borderRadius={{ base: "16px", md: "20px" }} boxShadow="panel" overflow="hidden">
        <HStack p={{ base: 4, md: 5 }} borderBottomWidth="1px" borderColor="#2b4437">
          <Box p={2.5} borderRadius="11px" bg="rgba(234,179,8,.1)" color="yellow.200"><WarningIcon /></Box>
          <Box>
            <Text fontWeight="800">{t("deviceLimit.penaltyStages")}</Text>
            <Text color="gray.400" fontSize="sm" mt={1}>{t("deviceLimit.penaltyStagesHelp")}</Text>
          </Box>
        </HStack>
        <Stack p={{ base: 4, md: 5 }} spacing={3}>
          {stageForm.map((stage, index) => (
            <SimpleGrid key={`${stage.violation_count}-${index}`} columns={{ base: 1, sm: 2, lg: 5 }} gap={3} p={3} borderWidth="1px" borderColor="rgba(148,163,184,.16)" borderRadius="11px" alignItems="end">
              <FormControl>
                <FormLabel fontSize="xs">{t("deviceLimit.violationNumber")}</FormLabel>
                <Input dir="ltr" type="number" min={1} value={stage.violation_count} onChange={(event) => updateStage(index, "violation_count", Number(event.target.value))} />
              </FormControl>
              <FormControl gridColumn={{ lg: "span 2" }}>
                <FormLabel fontSize="xs">{t("deviceLimit.action")}</FormLabel>
                <Select value={stage.action} onChange={(event) => updateStage(index, "action", event.target.value as PenaltyAction)}>
                  <option value="warn">{t("deviceLimit.actionWarn")}</option>
                  <option value="temporary_disable">{t("deviceLimit.actionTemporary")}</option>
                  <option value="permanent_disable">{t("deviceLimit.actionPermanent")}</option>
                  <option value="delete">{t("deviceLimit.actionDelete")}</option>
                </Select>
              </FormControl>
              <FormControl isDisabled={stage.action !== "temporary_disable"}>
                <FormLabel fontSize="xs">{t("deviceLimit.durationMinutes")}</FormLabel>
                <Input dir="ltr" type="number" min={1} value={secondsToMinutes(stage.duration_seconds)} onChange={(event) => updateStage(index, "duration_seconds", event.target.value ? Number(event.target.value) * 60 : null)} />
              </FormControl>
              <Checkbox minH="44px" colorScheme="primary" isChecked={stage.enabled} onChange={(event) => updateStage(index, "enabled", event.target.checked)}>{t("deviceLimit.stageEnabled")}</Checkbox>
            </SimpleGrid>
          ))}
          <HStack justify="space-between" flexWrap="wrap" gap={3}>
            <Button variant="outline" borderColor="#476858" onClick={() => setStageForm((current) => [...current, { violation_count: Math.max(0, ...current.map((stage) => stage.violation_count)) + 1, action: "warn", duration_seconds: null, enabled: true }])}>{t("deviceLimit.addStage")}</Button>
            <Button colorScheme="primary" color="#07130e" onClick={() => saveStages.mutate()} isLoading={saveStages.isLoading}>{t("save")}</Button>
          </HStack>
        </Stack>
      </Card>
    </Stack>
  );
};

const IncidentSection: FC = () => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [unresolved, setUnresolved] = useState(false);
  const query = useQuery<DeviceLimitIncidentList, Error>(
    ["device-limit-incidents", page, unresolved],
    () => fetch(`/device-limit/incidents?offset=${page * PAGE_SIZE}&limit=${PAGE_SIZE}&unresolved_only=${unresolved}`),
    { keepPreviousData: true }
  );
  const incidents = query.data?.incidents || [];
  const total = query.data?.total || 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const deleteWarning = useMutation(
    (incidentId: number) => fetch(`/device-limit/warnings/${incidentId}`, { method: "DELETE" }),
    {
      onSuccess: () => {
        queryClient.invalidateQueries("device-limit-incidents");
        toast({ title: t("deviceLimit.warningDeleted"), status: "success", duration: 2500 });
      },
    }
  );

  return (
    <Card mt={5} bg="#0e1914" color="gray.100" borderWidth="1px" borderColor="#345346" borderRadius={{ base: "16px", md: "20px" }} boxShadow="panel" overflow="hidden">
      <HStack p={{ base: 4, md: 5 }} borderBottomWidth="1px" borderColor="#2b4437" align="start" flexWrap="wrap">
        <Box p={2.5} borderRadius="11px" bg="rgba(239,68,68,.1)" color="red.200"><WarningIcon /></Box>
        <Box minW={0}>
          <Text fontWeight="800">{t("deviceLimit.incidents")}</Text>
          <Text color="gray.400" fontSize="sm" mt={1}>{t("deviceLimit.incidentsHelp", { count: total })}</Text>
        </Box>
        <HStack ms="auto">
          <Checkbox colorScheme="red" isChecked={unresolved} onChange={(event) => { setUnresolved(event.target.checked); setPage(0); }}>{t("deviceLimit.unresolvedOnly")}</Checkbox>
          <Button aria-label={t("refresh")} size="sm" minW="40px" variant="outline" borderColor="#476858" onClick={() => query.refetch()} isLoading={query.isFetching}><RefreshIcon /></Button>
        </HStack>
      </HStack>
      {query.isError && <Alert status="error" m={4} w="auto"><AlertIcon />{t("deviceLimit.loadFailed")}</Alert>}
      {query.isLoading ? (
        <Stack p={5}>{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} h="112px" borderRadius="11px" startColor="#14231b" endColor="#243d31" />)}</Stack>
      ) : incidents.length === 0 ? (
        <VStack py={14} px={5}><LimitIcon color="green.200" /><Text fontWeight="700">{t("deviceLimit.noIncidents")}</Text></VStack>
      ) : (
        <Stack p={{ base: 4, md: 5 }} spacing={3} divider={<Divider borderColor="rgba(148,163,184,.12)" />}>
          {incidents.map((incident) => (
            <Box key={incident.id} minW={0}>
              <HStack justify="space-between" align="start" gap={3} flexWrap="wrap">
                <Box minW={0}>
                  <HStack spacing={2} flexWrap="wrap">
                    <Text dir="ltr" fontFamily="mono" fontWeight="800" sx={{ unicodeBidi: "isolate" }}>{incident.username}</Text>
                    <Badge colorScheme={incident.resolved_at ? "gray" : "red"} variant="subtle">{t(`deviceLimit.action.${incident.action}`)}</Badge>
                    <Badge colorScheme="yellow" variant="outline">{t("deviceLimit.stage", { count: incident.stage })}</Badge>
                  </HStack>
                  <Text color="gray.300" fontSize="sm" mt={2} lineHeight="1.7">{incident.reason}</Text>
                  <HStack mt={2} spacing={2}>
                    <Badge variant="outline" colorScheme="cyan">{t(`deviceLimit.eventState.${incident.event_state}`)}</Badge>
                    {incident.risk_score !== null && <Badge variant="outline" colorScheme="orange">{t(`deviceLimit.riskLevel.${riskKey(incident.risk_score)}`)}</Badge>}
                    {incident.event_state === "warning" && !incident.resolved_at && (
                      <Button size="xs" variant="ghost" colorScheme="red" isLoading={deleteWarning.isLoading} onClick={() => deleteWarning.mutate(incident.id)}>{t("deviceLimit.deleteWarning")}</Button>
                    )}
                  </HStack>
                </Box>
                <Text dir="ltr" color="gray.400" fontSize="xs">{new Intl.DateTimeFormat(i18n.language, { dateStyle: "medium", timeStyle: "short" }).format(new Date(`${incident.created_at}Z`))}</Text>
              </HStack>
              <SimpleGrid columns={{ base: 1, sm: 3 }} gap={2} mt={3}>
                <Box p={2.5} bg="rgba(2,6,23,.32)" borderRadius="9px"><Text fontSize="xs" color="gray.400">{t("deviceLimit.observed")}</Text><Text mt={1} fontFamily="mono" fontWeight="800" dir="ltr">{incident.observed_count} / {incident.configured_limit}</Text></Box>
                <Box p={2.5} bg="rgba(2,6,23,.32)" borderRadius="9px" minW={0}><Text fontSize="xs" color="gray.400">{t("deviceLimit.ipAddresses")}</Text><Text mt={1} fontFamily="mono" fontSize="xs" dir="ltr" overflowWrap="anywhere">{incident.ip_addresses?.join(" · ") || "—"}</Text></Box>
                <Box p={2.5} bg="rgba(2,6,23,.32)" borderRadius="9px" minW={0}><Text fontSize="xs" color="gray.400">{t("deviceLimit.sources")}</Text><Text mt={1} fontFamily="mono" fontSize="xs" dir="ltr" overflowWrap="anywhere">{incident.source_nodes?.join(" · ") || "—"}</Text></Box>
              </SimpleGrid>
            </Box>
          ))}
        </Stack>
      )}
      <HStack justify="space-between" p={4} borderTopWidth="1px" borderColor="#2b4437">
        <Text color="gray.400" fontSize="sm">{t("deviceLimit.page", { current: page + 1, total: pages })}</Text>
        <HStack>
          <Button aria-label={t("previous")} size="sm" minW="40px" variant="outline" borderColor="#476858" isDisabled={page === 0} onClick={() => setPage((value) => value - 1)}><ChevronRightIcon width={16} /></Button>
          <Button aria-label={t("next")} size="sm" minW="40px" variant="outline" borderColor="#476858" isDisabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((value) => value + 1)}><ChevronLeftIcon width={16} /></Button>
        </HStack>
      </HStack>
    </Card>
  );
};

export const DeviceLimits: FC = () => {
  const { t } = useTranslation();
  const { userData, getUserIsPending } = useGetUser();
  const isOwner = userData.is_sudo || userData.role === "OWNER";
  const settings = useQuery<DeviceLimitSettings, Error>("device-limit-settings", () => fetch("/device-limit/settings"), { enabled: !getUserIsPending && isOwner });
  const stages = useQuery<DeviceLimitPenaltyStage[], Error>("device-limit-stages", () => fetch("/device-limit/penalty-stages"), { enabled: !getUserIsPending && isOwner });

  return (
    <AppShell>
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} gap={4} mb={6}>
        <Box>
          <HStack color="green.200" spacing={2}><LimitIcon /><Text fontSize="xs" fontWeight="800" letterSpacing=".13em" textTransform="uppercase">{t("deviceLimit.eyebrow")}</Text></HStack>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-.035em" mt={2}>{t("deviceLimit.title")}</Text>
          <Text color="gray.300" mt={1} maxW="720px">{t("deviceLimit.subtitle")}</Text>
        </Box>
        {isOwner && <Badge px={3} py={2} borderRadius="full" colorScheme={settings.data?.enabled ? "green" : "gray"} textTransform="none">{t(settings.data?.enabled ? "deviceLimit.active" : "deviceLimit.inactive")}</Badge>}
      </Stack>
      {isOwner && (settings.isError || stages.isError) && <Alert status="error" mb={4}><AlertIcon />{t("deviceLimit.loadFailed")}</Alert>}
      {isOwner && (settings.data && stages.data ? <SettingsSection settings={settings.data} stages={stages.data} /> : <Stack>{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} h="180px" borderRadius="18px" startColor="#14231b" endColor="#243d31" />)}</Stack>)}
      <IncidentSection />
    </AppShell>
  );
};

export default DeviceLimits;
