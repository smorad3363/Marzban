import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  Code,
  Divider,
  FormControl,
  FormLabel,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalHeader,
  ModalOverlay,
  Select,
  SimpleGrid,
  Skeleton,
  Stack,
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
} from "@chakra-ui/react";
import {
  ArrowPathIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ClockIcon,
  DocumentMagnifyingGlassIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { AppShell } from "components/AppShell";
import useGetUser from "hooks/useGetUser";
import { FC, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "react-query";
import { fetch } from "service/http";
import { AuditLog, AuditLogList, AuditLogOptions, AuditValue } from "types/Audit";

const SearchIcon = chakra(MagnifyingGlassIcon, { baseStyle: { w: 4, h: 4 } });
const AuditIcon = chakra(DocumentMagnifyingGlassIcon, { baseStyle: { w: 5, h: 5 } });
const FilterIcon = chakra(FunnelIcon, { baseStyle: { w: 4, h: 4 } });
const RefreshIcon = chakra(ArrowPathIcon, { baseStyle: { w: 4, h: 4 } });
const PAGE_SIZE = 25;

const formatAuditDate = (value: string) => {
  const normalized = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    timeZone: "Asia/Tehran",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
    .format(new Date(normalized))
    .replace("،", " -");
};

const actionTone = (action: string, status: string) => {
  if (status === "failed") return { bg: "rgba(239,68,68,.15)", color: "red.200", border: "rgba(248,113,113,.35)" };
  if (action.includes("delete") || action.includes("deactivate")) return { bg: "rgba(239,68,68,.12)", color: "red.200", border: "rgba(248,113,113,.3)" };
  if (action.includes("create") || action.includes("activate")) return { bg: "rgba(34,197,94,.12)", color: "green.200", border: "rgba(74,222,128,.3)" };
  if (action.includes("traffic") || action.includes("expiration") || action.includes("renew")) return { bg: "rgba(6,182,212,.13)", color: "cyan.200", border: "rgba(34,211,238,.3)" };
  if (action.startsWith("bulk")) return { bg: "rgba(59,130,246,.14)", color: "blue.200", border: "rgba(96,165,250,.34)" };
  return { bg: "whiteAlpha.100", color: "gray.200", border: "whiteAlpha.200" };
};

const prettyJson = (value: AuditValue) => value == null ? "—" : JSON.stringify(value, null, 2);

const ActionBadge: FC<{ log: AuditLog }> = ({ log }) => {
  const tone = actionTone(log.action, log.status);
  return (
    <Badge px={2.5} py={1} borderRadius="full" textTransform="none" bg={tone.bg} color={tone.color} borderWidth="1px" borderColor={tone.border} fontFamily="mono" fontSize="10px">
      {log.action}
    </Badge>
  );
};

const ValuePanel: FC<{ title: string; value: AuditValue; accent: string }> = ({ title, value, accent }) => (
  <Box minW={0} bg="#0b1511" borderWidth="1px" borderColor="#2b4437" borderRadius="12px" overflow="hidden">
    <Text px={4} py={2.5} color={accent} bg="whiteAlpha.50" fontSize="xs" fontWeight="800" letterSpacing=".04em">{title}</Text>
    <Code display="block" maxH="280px" overflow="auto" p={4} bg="transparent" color="gray.200" whiteSpace="pre-wrap" wordBreak="break-word" fontSize="xs" lineHeight="1.8" dir="ltr">
      {prettyJson(value)}
    </Code>
  </Box>
);

const AuditDetails: FC<{ log: AuditLog | null; isOpen: boolean; onClose: () => void }> = ({ log, isOpen, onClose }) => {
  const { t, i18n } = useTranslation();
  if (!log) return null;
  return (
    <Modal isOpen={isOpen} onClose={onClose} size="4xl" scrollBehavior="inside">
      <ModalOverlay bg="rgba(0,0,0,.76)" backdropFilter="blur(5px)" />
      <ModalContent dir={i18n.dir()} mx={3} maxH="calc(100dvh - 24px)" bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#355546" borderRadius="16px" boxShadow="0 28px 80px rgba(0,0,0,.55)">
        <ModalHeader pe={14}>
          <HStack flexWrap="wrap"><ActionBadge log={log} /><Text fontSize="lg">{t("audit.detailsTitle")}</Text></HStack>
        </ModalHeader>
        <ModalCloseButton />
        <ModalBody pb={6}>
          <Stack spacing={4}>
            <Box p={4} bg="rgba(6,182,212,.06)" borderWidth="1px" borderColor="rgba(34,211,238,.2)" borderRadius="12px">
              <Text fontWeight="700" lineHeight="1.8">{log.description}</Text>
              <SimpleGrid columns={{ base: 1, sm: 2, lg: 4 }} gap={3} mt={3} fontSize="sm">
                <Box><Text color="gray.400" fontSize="xs">{t("audit.admin")}</Text><Text mt={1}>{log.admin_username}</Text></Box>
                <Box><Text color="gray.400" fontSize="xs">{t("audit.target")}</Text><Text mt={1}>{log.target_name || log.target_id || "—"}</Text></Box>
                <Box><Text color="gray.400" fontSize="xs">{t("audit.ip")}</Text><Text mt={1} dir="ltr">{log.ip_address || "—"}</Text></Box>
                <Box><Text color="gray.400" fontSize="xs">{t("audit.date")}</Text><Text mt={1} dir="ltr">{formatAuditDate(log.created_at)}</Text></Box>
              </SimpleGrid>
            </Box>
            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <ValuePanel title={t("audit.previousValue")} value={log.previous_value} accent="orange.200" />
              <ValuePanel title={t("audit.newValue")} value={log.new_value} accent="green.200" />
            </SimpleGrid>
            <ValuePanel title={t("audit.metadata")} value={log.details} accent="cyan.200" />
          </Stack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};

export const AuditLogs: FC = () => {
  const { t } = useTranslation();
  const { userData, getUserIsPending } = useGetUser();
  const details = useDisclosure();
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const [page, setPage] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [filters, setFilters] = useState({ search: "", admin: "", action: "", target: "", from: "", to: "", sort: "newest" });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((current) => ({ ...current, search: searchInput.trim() }));
      setPage(0);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const queryString = useMemo(() => {
    const params = new URLSearchParams({ offset: String(page * PAGE_SIZE), limit: String(PAGE_SIZE), sort: filters.sort });
    if (filters.search) params.set("search", filters.search);
    if (filters.admin) params.set("admin_username", filters.admin);
    if (filters.action) params.set("action", filters.action);
    if (filters.target) params.set("target", filters.target);
    if (filters.from) params.set("date_from", filters.from);
    if (filters.to) params.set("date_to", filters.to);
    return params.toString();
  }, [filters, page]);

  const optionsQuery = useQuery<AuditLogOptions>("audit-log-options", () => fetch("/audit-logs/options"), { enabled: !getUserIsPending });
  const logsQuery = useQuery<AuditLogList, Error>(["audit-logs", queryString], () => fetch(`/audit-logs?${queryString}`), { keepPreviousData: true, enabled: !getUserIsPending });
  const logs = logsQuery.data?.logs || [];
  const total = logsQuery.data?.total || 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const setFilter = (key: keyof typeof filters, value: string) => { setFilters((current) => ({ ...current, [key]: value })); setPage(0); };
  const clearFilters = () => { setSearchInput(""); setFilters({ search: "", admin: "", action: "", target: "", from: "", to: "", sort: "newest" }); setPage(0); };
  const showDetails = (log: AuditLog) => { setSelected(log); details.onOpen(); };

  return (
    <AppShell>
      <Stack direction={{ base: "column", md: "row" }} justify="space-between" align={{ md: "end" }} gap={4} mb={6}>
        <Box>
          <HStack color="cyan.200" spacing={2}><AuditIcon /><Text fontSize="xs" fontWeight="800" letterSpacing=".13em" textTransform="uppercase">{t("audit.eyebrow")}</Text></HStack>
          <Text as="h1" fontSize={{ base: "2xl", md: "3xl" }} fontWeight="800" letterSpacing="-.035em" mt={2}>{t("audit.title")}</Text>
          <Text color="gray.300" mt={1} maxW="680px">{t("audit.subtitle")}</Text>
        </Box>
        <HStack bg="rgba(34,197,94,.08)" color="green.200" borderWidth="1px" borderColor="rgba(74,222,128,.25)" borderRadius="full" px={3} py={2} fontSize="xs">
          <ShieldCheckIcon width={16} aria-hidden="true" /><Text>{t("audit.appendOnly")}</Text>
        </HStack>
      </Stack>

      <Card bg="linear-gradient(145deg, rgba(17,29,23,.98), rgba(10,24,27,.96))" color="gray.100" borderWidth="1px" borderColor="#345346" borderRadius={{ base: "16px", md: "20px" }} boxShadow="panel" overflow="hidden">
        <Box p={{ base: 4, md: 5 }} borderBottomWidth="1px" borderColor="#2b4437">
          <HStack mb={4} color="gray.200"><FilterIcon /><Text fontWeight="700">{t("audit.filters")}</Text><Text ms="auto" fontSize="xs" color="gray.400">{t("audit.resultCount", { count: total })}</Text></HStack>
          <InputGroup mb={4}>
            <InputLeftElement pointerEvents="none" color="gray.400"><SearchIcon /></InputLeftElement>
            <Input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder={t("audit.searchPlaceholder")} minH="44px" />
          </InputGroup>
          <SimpleGrid columns={{ base: 1, sm: 2, xl: 6 }} gap={3}>
            <FormControl><FormLabel fontSize="xs">{t("audit.admin")}</FormLabel><Select value={filters.admin} onChange={(e) => setFilter("admin", e.target.value)}><option value="">{t("audit.allAdmins")}</option>{optionsQuery.data?.admins.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
            <FormControl><FormLabel fontSize="xs">{t("audit.action")}</FormLabel><Select value={filters.action} onChange={(e) => setFilter("action", e.target.value)}><option value="">{t("audit.allActions")}</option>{optionsQuery.data?.actions.map((item) => <option key={item} value={item}>{item}</option>)}</Select></FormControl>
            <FormControl><FormLabel fontSize="xs">{t("audit.target")}</FormLabel><Input value={filters.target} onChange={(e) => setFilter("target", e.target.value)} placeholder={t("audit.targetPlaceholder")} /></FormControl>
            <FormControl><FormLabel fontSize="xs">{t("audit.fromDate")}</FormLabel><Input type="date" dir="ltr" value={filters.from} onChange={(e) => setFilter("from", e.target.value)} /></FormControl>
            <FormControl><FormLabel fontSize="xs">{t("audit.toDate")}</FormLabel><Input type="date" dir="ltr" value={filters.to} onChange={(e) => setFilter("to", e.target.value)} /></FormControl>
            <FormControl><FormLabel fontSize="xs">{t("audit.sort")}</FormLabel><Select value={filters.sort} onChange={(e) => setFilter("sort", e.target.value)}><option value="newest">{t("audit.newest")}</option><option value="oldest">{t("audit.oldest")}</option></Select></FormControl>
          </SimpleGrid>
          <HStack mt={4} justify="end" flexWrap="wrap">
            <Button size="sm" variant="ghost" onClick={clearFilters}>{t("audit.clear")}</Button>
            <Button size="sm" variant="outline" borderColor="#476858" leftIcon={<RefreshIcon />} onClick={() => logsQuery.refetch()} isLoading={logsQuery.isFetching}>{t("refresh")}</Button>
          </HStack>
        </Box>

        {logsQuery.isError && <Alert status="error" m={4} w="auto"><AlertIcon />{t("audit.loadFailed")}<Button size="sm" ms="auto" onClick={() => logsQuery.refetch()}>{t("retry")}</Button></Alert>}
        {logsQuery.isLoading ? (
          <Stack p={5}>{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} startColor="#14231b" endColor="#243d31" h="56px" borderRadius="9px" />)}</Stack>
        ) : logs.length === 0 ? (
          <VStack py={16} px={5} spacing={3}><Box p={3} borderRadius="full" bg="rgba(6,182,212,.1)" color="cyan.200"><AuditIcon /></Box><Text fontWeight="700">{t("audit.empty")}</Text><Text color="gray.400" fontSize="sm" textAlign="center">{t("audit.emptyHelp")}</Text></VStack>
        ) : (
          <>
            <TableContainer display={{ base: "none", lg: "block" }}>
              <Table size="sm"><Thead><Tr><Th>{t("audit.admin")}</Th><Th>{t("audit.action")}</Th><Th>{t("audit.target")}</Th><Th>{t("audit.description")}</Th><Th>{t("audit.date")}</Th><Th textAlign="end">{t("audit.details")}</Th></Tr></Thead>
                <Tbody>{logs.map((log) => <Tr key={log.id} _hover={{ bg: "rgba(6,182,212,.035)" }}>
                  <Td><Text color="white" fontWeight="700">{log.admin_username}</Text><Text color="gray.500" fontSize="xs" dir="ltr">{log.ip_address || "—"}</Text></Td>
                  <Td><ActionBadge log={log} /></Td>
                  <Td><Text maxW="170px" noOfLines={1}>{log.target_name || log.target_id || "—"}</Text><Text color="gray.500" fontSize="xs">{log.target_type}</Text></Td>
                  <Td maxW="430px"><Text noOfLines={2} lineHeight="1.7">{log.description}</Text></Td>
                  <Td whiteSpace="nowrap"><HStack spacing={1.5}><ClockIcon width={15} color="#67e8f9" aria-hidden="true" /><Text dir="ltr" fontSize="xs">{formatAuditDate(log.created_at)}</Text></HStack></Td>
                  <Td textAlign="end"><Button size="xs" variant="outline" borderColor="#476858" onClick={() => showDetails(log)}>{t("audit.details")}</Button></Td>
                </Tr>)}</Tbody>
              </Table>
            </TableContainer>

            <Stack display={{ base: "flex", lg: "none" }} divider={<Divider borderColor="#2b4437" />} spacing={0}>
              {logs.map((log) => <Box key={log.id} p={4} role="group">
                <HStack justify="space-between" align="start" gap={3}><Box minW={0}><Text color="white" fontWeight="750" noOfLines={1}>{log.admin_username}</Text><Text color="gray.400" fontSize="xs" mt={1} noOfLines={1}>{log.target_name || log.target_id || log.target_type}</Text></Box><ActionBadge log={log} /></HStack>
                <Text my={3} lineHeight="1.8" fontSize="sm">{log.description}</Text>
                <HStack justify="space-between" align="center" gap={3}><Text dir="ltr" color="gray.400" fontSize="xs">{formatAuditDate(log.created_at)}</Text><Button size="sm" minH="40px" variant="outline" borderColor="#476858" onClick={() => showDetails(log)}>{t("audit.details")}</Button></HStack>
              </Box>)}
            </Stack>
          </>
        )}

        <HStack justify="space-between" p={4} borderTopWidth="1px" borderColor="#2b4437" gap={3}>
          <Text fontSize="sm" color="gray.400">{t("audit.page", { current: page + 1, total: pages })}</Text>
          <HStack><Button aria-label={t("previous")} size="sm" minW="40px" variant="outline" borderColor="#476858" isDisabled={page === 0} onClick={() => setPage((value) => value - 1)}><ChevronRightIcon width={16} /></Button><Button aria-label={t("next")} size="sm" minW="40px" variant="outline" borderColor="#476858" isDisabled={(page + 1) * PAGE_SIZE >= total} onClick={() => setPage((value) => value + 1)}><ChevronLeftIcon width={16} /></Button></HStack>
        </HStack>
      </Card>
      <AuditDetails log={selected} isOpen={details.isOpen} onClose={details.onClose} />
    </AppShell>
  );
};

export default AuditLogs;
