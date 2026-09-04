import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Divider,
  HStack,
  IconButton,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  Tooltip,
  chakra,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import {
  CheckIcon,
  ClipboardIcon,
  DevicePhoneMobileIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { FC, useEffect, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { localizedApiError } from "utils/apiError";
import { DeviceClientObservation, DeviceLimitState, DeviceLimitUserSummary } from "types/DeviceLimit";
import { User } from "types/User";

const iconProps = { baseStyle: { w: 4, h: 4 } };
const WarningIcon = chakra(ExclamationTriangleIcon, iconProps);
const SafeIcon = chakra(ShieldCheckIcon, iconProps);
const DeviceIcon = chakra(DevicePhoneMobileIcon, iconProps);
const CopyIcon = chakra(ClipboardIcon, iconProps);
const CopiedIcon = chakra(CheckIcon, iconProps);

const isPenalty = (state?: DeviceLimitState | null) =>
  Boolean(state && state.penalty_status !== "clear");

const ClientDetails: FC<{ observation: DeviceClientObservation; locale: string }> = ({ observation, locale }) => {
  const { t } = useTranslation();
  const formatDate = (value: string) => new Intl.DateTimeFormat(locale, { dateStyle: "short", timeStyle: "short" }).format(new Date(`${value}Z`));
  return (
    <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} gap={2} mt={2} p={2.5} bg="rgba(2,6,23,.28)" borderRadius="9px">
      <Box><Text color="gray.400" fontSize="xs">{t("deviceLimit.client")}</Text><Text dir="ltr" fontFamily="mono" fontSize="xs">{observation.client_name} {observation.client_version || ""}</Text></Box>
      <Box><Text color="gray.400" fontSize="xs">{t("deviceLimit.platform")}</Text><Text dir="ltr" fontFamily="mono" fontSize="xs">{observation.platform || observation.os_token || "—"}</Text></Box>
      <Box><Text color="gray.400" fontSize="xs">{t("deviceLimit.lastSeen")}</Text><Text dir="ltr" fontFamily="mono" fontSize="xs">{formatDate(observation.last_seen_at)}</Text></Box>
      <Box><Text color="gray.400" fontSize="xs">{t("deviceLimit.subscriptionSeen")}</Text><Text dir="ltr" fontFamily="mono" fontSize="xs">{observation.seen_count}</Text></Box>
      {observation.network_stack && <Box gridColumn={{ sm: "span 2" }}><Text color="gray.400" fontSize="xs">{t("deviceLimit.networkStack")}</Text><Text dir="ltr" fontFamily="mono" fontSize="xs">{observation.network_stack}</Text></Box>}
      {observation.raw_user_agent && <Box gridColumn={{ sm: "span 2" }} minW={0}><Text color="gray.400" fontSize="xs">User-Agent</Text><Text dir="ltr" fontFamily="mono" fontSize="xs" overflowWrap="anywhere">{observation.raw_user_agent}</Text></Box>}
    </SimpleGrid>
  );
};

export const UserDeviceLimit: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const disclosure = useDisclosure();
  const [copiedSlot, setCopiedSlot] = useState<number | null>(null);
  const warned = isPenalty(user.device_limit_state);
  const query = useQuery<DeviceLimitUserSummary, Error>(
    ["device-limit-user", user.username],
    () => fetch(`/device-limit/users/${encodeURIComponent(user.username)}`),
    { enabled: disclosure.isOpen, refetchOnWindowFocus: false }
  );

  useEffect(() => {
    if (copiedSlot === null) return;
    const timer = window.setTimeout(() => setCopiedSlot(null), 1200);
    return () => window.clearTimeout(timer);
  }, [copiedSlot]);

  const stateMutation = useMutation(
    (action: "reset-strikes" | "unblock") => fetch(
      `/device-limit/users/${encodeURIComponent(user.username)}/${action}`,
      { method: "POST" }
    ),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(["device-limit-user", user.username]);
        queryClient.invalidateQueries("users");
        toast({ title: t("deviceLimit.userActionSaved"), status: "success", duration: 3000 });
      },
      onError: (error: any) => {
        toast({
          title: t("deviceLimit.saveFailed"),
          description: localizedApiError(error),
          status: "error",
          duration: 5000,
        });
      },
    }
  );

  if (user.concurrent_user_limit == null) return null;

  const summary = query.data;
  const state = summary?.state || user.device_limit_state;
  const hasPenalty = isPenalty(state);

  return (
    <>
      <Tooltip label={t(hasPenalty || warned ? "deviceLimit.openWarning" : "deviceLimit.openDevices")} placement="top">
        <IconButton
          aria-label={t(hasPenalty || warned ? "deviceLimit.openWarning" : "deviceLimit.openDevices")}
          icon={hasPenalty || warned ? <WarningIcon /> : <SafeIcon />}
          size="sm"
          minW="44px"
          h="44px"
          borderRadius="9px"
          variant="outline"
          color={hasPenalty || warned ? "yellow.200" : "green.200"}
          borderColor={hasPenalty || warned ? "rgba(234,179,8,.5)" : "rgba(34,197,94,.4)"}
          bg={hasPenalty || warned ? "rgba(234,179,8,.08)" : "rgba(34,197,94,.06)"}
          _hover={{ bg: hasPenalty || warned ? "rgba(234,179,8,.15)" : "rgba(34,197,94,.13)" }}
          onClick={(event) => { event.stopPropagation(); disclosure.onOpen(); }}
        />
      </Tooltip>

      <Modal isOpen={disclosure.isOpen} onClose={disclosure.onClose} size="4xl" scrollBehavior="inside">
        <ModalOverlay bg="rgba(0,0,0,.76)" backdropFilter="blur(5px)" />
        <ModalContent mx={3} my={3} maxH="calc(100dvh - 24px)" dir={i18n.dir()} bg="#0c1712" color="gray.100" borderWidth="1px" borderColor="#345346" borderRadius={{ base: "14px", md: "18px" }} boxShadow="0 24px 70px rgba(0,0,0,.58)">
          <ModalHeader pe={14}>
            <HStack align="start">
              <Box p={2.5} borderRadius="11px" bg={hasPenalty ? "rgba(234,179,8,.12)" : "rgba(34,197,94,.1)"} color={hasPenalty ? "yellow.200" : "green.200"}>{hasPenalty ? <WarningIcon /> : <SafeIcon />}</Box>
              <Box minW={0}>
                <Text>{t("deviceLimit.userTitle")}</Text>
                <Text dir="ltr" fontFamily="mono" color="gray.400" fontSize="sm" mt={1} sx={{ unicodeBidi: "isolate" }}>{user.username}</Text>
              </Box>
            </HStack>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            {query.isError && <Alert status="error"><AlertIcon />{t("deviceLimit.loadFailed")}</Alert>}
            {query.isLoading || !summary ? (
              <Stack>{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} h="112px" borderRadius="11px" startColor="#14231b" endColor="#243d31" />)}</Stack>
            ) : (
              <Stack spacing={4}>
                <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} gap={3}>
                  <Box p={3} bg="rgba(2,6,23,.34)" borderWidth="1px" borderColor="rgba(148,163,184,.15)" borderRadius="10px"><Text color="gray.400" fontSize="xs">{t("deviceLimit.configuredLimit")}</Text><Text mt={1} dir="ltr" fontFamily="mono" fontWeight="900">{summary.configured_limit ?? "∞"}</Text></Box>
                  <Box p={3} bg="rgba(2,6,23,.34)" borderWidth="1px" borderColor="rgba(148,163,184,.15)" borderRadius="10px"><Text color="gray.400" fontSize="xs">{t("deviceLimit.liveConnections")}</Text><Text mt={1} dir="ltr" fontFamily="mono" fontWeight="900">{summary.live_active_ip_count}</Text></Box>
                  <Box p={3} bg="rgba(2,6,23,.34)" borderWidth="1px" borderColor="rgba(148,163,184,.15)" borderRadius="10px"><Text color="gray.400" fontSize="xs">{t("deviceLimit.strikes")}</Text><Text mt={1} dir="ltr" fontFamily="mono" fontWeight="900">{summary.state.violation_count}</Text></Box>
                  <Box p={3} bg="rgba(2,6,23,.34)" borderWidth="1px" borderColor="rgba(148,163,184,.15)" borderRadius="10px"><Text color="gray.400" fontSize="xs">{t("deviceLimit.penaltyStatus")}</Text><Badge mt={1} colorScheme={summary.state.penalty_status === "clear" ? "green" : "yellow"} textTransform="none">{t(`deviceLimit.status.${summary.state.penalty_status}`)}</Badge></Box>
                </SimpleGrid>

                {summary.state.last_reason && (
                  <Alert status="warning" borderRadius="10px" alignItems="start"><AlertIcon mt={0.5} /><Box><Text fontWeight="750">{t("deviceLimit.lastWarning")}</Text><Text fontSize="sm" mt={1}>{summary.state.last_reason}</Text></Box></Alert>
                )}

                <Box p={4} bg="#101e17" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
                  <Text fontWeight="800">{t("deviceLimit.liveActivity")}</Text>
                  <SimpleGrid columns={{ base: 1, md: 2 }} gap={3} mt={3}>
                    <Box minW={0}><Text color="gray.400" fontSize="xs">{t("deviceLimit.ipAddresses")}</Text><Text dir="ltr" mt={1} fontFamily="mono" fontSize="xs" overflowWrap="anywhere">{summary.live_ip_addresses.join(" · ") || "—"}</Text></Box>
                    <Box minW={0}><Text color="gray.400" fontSize="xs">{t("deviceLimit.sources")}</Text><Text dir="ltr" mt={1} fontFamily="mono" fontSize="xs" overflowWrap="anywhere">{summary.live_source_nodes.join(" · ") || "—"}</Text></Box>
                  </SimpleGrid>
                </Box>

                <Box p={4} bg="#101e17" borderWidth="1px" borderColor="#33483b" borderRadius="12px">
                  <HStack><DeviceIcon color="green.200" /><Text fontWeight="800">{t("deviceLimit.deviceSlots")}</Text><Badge ms="auto" colorScheme="green">{summary.slots.length}</Badge></HStack>
                  <Stack mt={3} divider={<Divider borderColor="rgba(148,163,184,.12)" />}>
                    {summary.slots.map((slot) => {
                      const link = slot.subscription_url.startsWith("/") ? window.location.origin + slot.subscription_url : slot.subscription_url;
                      return (
                        <Box key={slot.id} py={2} minW={0}>
                          <HStack justify="space-between" align="center" gap={3} minW={0}>
                            <Box minW={0}>
                              <Text fontWeight="700">{slot.label || t("deviceLimit.deviceNumber", { count: slot.slot_index })}</Text>
                              <Text dir="ltr" color="gray.400" fontFamily="mono" fontSize="xs" mt={1} noOfLines={1} sx={{ unicodeBidi: "isolate" }}>{slot.last_ip || t("deviceLimit.neverSeen")}</Text>
                            </Box>
                            <CopyToClipboard text={link} onCopy={() => setCopiedSlot(slot.slot_index)}>
                              <Button minH="44px" variant="outline" borderColor="#476858" leftIcon={copiedSlot === slot.slot_index ? <CopiedIcon /> : <CopyIcon />}>{t(copiedSlot === slot.slot_index ? "usersTable.copied" : "deviceLimit.copySlotLink")}</Button>
                            </CopyToClipboard>
                          </HStack>
                          {slot.client_observations[0] && <ClientDetails observation={slot.client_observations[0]} locale={i18n.language} />}
                        </Box>
                      );
                    })}
                  </Stack>
                  {summary.user_client_observations[0] && (
                    <Box mt={3} pt={3} borderTopWidth="1px" borderColor="rgba(148,163,184,.12)">
                      <Text fontSize="sm" fontWeight="700">{t("deviceLimit.legacyClientObservation")}</Text>
                      <ClientDetails observation={summary.user_client_observations[0]} locale={i18n.language} />
                    </Box>
                  )}
                </Box>
              </Stack>
            )}
          </ModalBody>
          <ModalFooter borderTopWidth="1px" borderColor="#2b4437" gap={3} flexWrap="wrap">
            <Button minH="44px" variant="outline" borderColor="#476858" onClick={() => stateMutation.mutate("reset-strikes")} isLoading={stateMutation.isLoading}>{t("deviceLimit.resetStrikes")}</Button>
            {state && state.penalty_status !== "clear" && <Button minH="44px" colorScheme="primary" color="#07130e" onClick={() => stateMutation.mutate("unblock")} isLoading={stateMutation.isLoading}>{t("deviceLimit.unblock")}</Button>}
            <Button minH="44px" variant="ghost" onClick={disclosure.onClose}>{t("cancel")}</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </>
  );
};
