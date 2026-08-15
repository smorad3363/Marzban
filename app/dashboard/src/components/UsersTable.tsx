import {
  Box,
  Button,
  Card,
  chakra,
  HStack,
  IconButton,
  Progress,
  Stack,
  Table,
  TableContainer,
  TableProps,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  VStack,
} from "@chakra-ui/react";
import {
  CheckIcon,
  ChevronDownIcon,
  ClipboardIcon,
  LinkIcon,
  PencilIcon,
  QrCodeIcon,
} from "@heroicons/react/24/outline";
import { ReactComponent as AddFileIcon } from "assets/add_file.svg";
import classNames from "classnames";
import { resetStrategy, statusColors } from "constants/UserSettings";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { User } from "types/User";
import { formatBytes } from "utils/formatByte";
import { OnlineBadge } from "./OnlineBadge";
import { OnlineStatus } from "./OnlineStatus";
import { Pagination } from "./Pagination";
import { StatusBadge } from "./StatusBadge";

const EmptySectionIcon = chakra(AddFileIcon);
const iconProps = { baseStyle: { w: 4, h: 4 } };
const CopyIcon = chakra(ClipboardIcon, iconProps);
const CopiedIcon = chakra(CheckIcon, iconProps);
const SubscriptionLinkIcon = chakra(LinkIcon, iconProps);
const QRIcon = chakra(QrCodeIcon, iconProps);
const EditIcon = chakra(PencilIcon, iconProps);
const SortIcon = chakra(ChevronDownIcon, { baseStyle: { w: 3.5, h: 3.5 } });

type UsageMeterProps = {
  used: number;
  total: number | null;
  dataLimitResetStrategy: string | null;
  totalUsedTraffic: number;
  colorScheme?: string;
  compact?: boolean;
};

const getResetStrategy = (strategy: string): string => {
  const entry = resetStrategy.find((item) => item.value === strategy);
  return entry?.title || "No";
};

const UsageMeter: FC<UsageMeterProps> = ({
  used,
  total,
  dataLimitResetStrategy,
  totalUsedTraffic,
  colorScheme = "primary",
  compact,
}) => {
  const { t, i18n } = useTranslation();
  const direction = i18n.dir();
  const isUnlimited = total === 0 || total === null;
  const percent = isUnlimited ? 100 : Math.min((used / Math.max(total, 1)) * 100, 100);
  const isReached = !isUnlimited && percent >= 100;
  const limitText = isUnlimited
    ? "∞"
    : formatBytes(total) +
      (dataLimitResetStrategy && dataLimitResetStrategy !== "no_reset"
        ? ` ${t(`userDialog.resetStrategy${getResetStrategy(dataLimitResetStrategy)}`)}`
        : "");

  return (
    <Stack spacing={compact ? 1 : 2} minW={0} dir={direction}>
      {!compact && (
        <Progress
          value={percent}
          size="xs"
          colorScheme={isReached ? "red" : colorScheme}
          borderRadius="full"
          opacity={isUnlimited ? 0.45 : 1}
          aria-label={`${formatBytes(used)} / ${limitText}`}
        />
      )}
      <HStack justify="space-between" align="start" gap={3} color="gray.600" _dark={{ color: "gray.300" }} fontSize="xs" fontFamily="mono">
        <Text dir="ltr" textAlign="start" overflowWrap="anywhere" sx={{ unicodeBidi: "isolate" }}>{formatBytes(used)} / <Text as="span" fontFamily="mono">{limitText}</Text></Text>
        {!compact && <Text flexShrink={0}>{t("usersTable.total")}: <Text as="span" dir="ltr" display="inline-block" sx={{ unicodeBidi: "isolate" }}>{formatBytes(totalUsedTraffic)}</Text></Text>}
      </HStack>
    </Stack>
  );
};

type SortLabelProps = {
  label: string;
  column: string;
  sort: string;
  onSort: (column: string) => void;
};

const SortLabel: FC<SortLabelProps> = ({ label, column, sort, onSort }) => {
  const active = sort.includes(column);
  return (
    <Button
      size="xs"
      variant="unstyled"
      display="inline-flex"
      alignItems="center"
      gap={1.5}
      minH="32px"
      color="inherit"
      fontSize="inherit"
      fontWeight="inherit"
      textTransform="inherit"
      letterSpacing="inherit"
      onClick={() => onSort(column)}
      aria-label={`${label}: sort`}
    >
      {label}
      {active && <SortIcon aria-hidden="true" transform={sort.startsWith("-") ? undefined : "rotate(180deg)"} />}
    </Button>
  );
};

type ActionButtonsProps = { user: User };

const ActionButtons: FC<ActionButtonsProps> = ({ user }) => {
  const { setQRCode, setSubLink, onEditingUser } = useDashboard();
  const { t, i18n } = useTranslation();
  const isRtl = i18n.dir() === "rtl";
  const proxyLinks = user.links.join("\r\n");
  const [copied, setCopied] = useState<[number, boolean]>([-1, false]);

  useEffect(() => {
    if (!copied[1]) return;
    const timer = window.setTimeout(() => setCopied([-1, false]), 1200);
    return () => window.clearTimeout(timer);
  }, [copied]);

  const buttonStyle = {
    variant: "ghost",
    size: "sm",
    color: "gray.600",
    _dark: { color: "gray.200", _hover: { bg: "whiteAlpha.100", color: "white" } },
  } as const;

  return (
    <HStack dir="ltr" justify={isRtl ? "flex-start" : "flex-end"} spacing={1} flexWrap="wrap" onClick={(event) => event.stopPropagation()}>
      <CopyToClipboard
        text={user.subscription_url.startsWith("/") ? window.location.origin + user.subscription_url : user.subscription_url}
        onCopy={() => setCopied([0, true])}
      >
        <Box>
          <Tooltip label={copied[0] === 0 && copied[1] ? t("usersTable.copied") : t("usersTable.copyLink")} placement="top">
            <IconButton {...buttonStyle} aria-label={t("usersTable.copyLink")} icon={copied[0] === 0 && copied[1] ? <CopiedIcon /> : <SubscriptionLinkIcon />} />
          </Tooltip>
        </Box>
      </CopyToClipboard>
      <CopyToClipboard text={proxyLinks} onCopy={() => setCopied([1, true])}>
        <Box>
          <Tooltip label={copied[0] === 1 && copied[1] ? t("usersTable.copied") : t("usersTable.copyConfigs")} placement="top">
            <IconButton {...buttonStyle} aria-label={t("usersTable.copyConfigs")} icon={copied[0] === 1 && copied[1] ? <CopiedIcon /> : <CopyIcon />} />
          </Tooltip>
        </Box>
      </CopyToClipboard>
      <Tooltip label="QR Code" placement="top">
        <IconButton
          {...buttonStyle}
          aria-label="QR Code"
          icon={<QRIcon />}
          onClick={() => {
            setQRCode(user.links);
            setSubLink(user.subscription_url);
          }}
        />
      </Tooltip>
      <Tooltip label={t("userDialog.editUser")} placement="top">
        <IconButton {...buttonStyle} aria-label={t("userDialog.editUser")} icon={<EditIcon />} onClick={() => onEditingUser(user)} />
      </Tooltip>
    </HStack>
  );
};

const EmptySection: FC<{ isFiltered: boolean }> = ({ isFiltered }) => {
  const { onCreateUser } = useDashboard();
  const { t } = useTranslation();
  return (
    <VStack px={5} py={12} spacing={4} textAlign="center">
      <EmptySectionIcon
        maxH="150px"
        maxW="150px"
        aria-hidden="true"
        _dark={{
          'path[fill="#fff"]': { fill: "gray.800" },
          'path[fill="#f2f2f2"], path[fill="#e6e6e6"], path[fill="#ccc"]': { fill: "gray.700" },
          'circle[fill="#3182CE"]': { fill: "primary.300" },
        }}
        _light={{
          'path[fill="#f2f2f2"], path[fill="#e6e6e6"], path[fill="#ccc"]': { fill: "gray.300" },
          'circle[fill="#3182CE"]': { fill: "primary.500" },
        }}
      />
      <Text color="gray.600" _dark={{ color: "gray.300" }} maxW="52ch">
        {isFiltered ? t("usersTable.noUserMatched") : t("usersTable.noUser")}
      </Text>
      {!isFiltered && <Button size="sm" colorScheme="primary" onClick={() => onCreateUser(true)}>{t("createUser")}</Button>}
    </VStack>
  );
};

type UsersTableProps = TableProps;

export const UsersTable: FC<UsersTableProps> = (props) => {
  const {
    filters,
    users: { users },
    onEditingUser,
    onFilterChange,
  } = useDashboard();
  const { t, i18n } = useTranslation();
  const direction = i18n.dir();
  const isFiltered = Boolean(filters.search || filters.status);

  const handleSort = (column: string) => {
    let newSort = filters.sort;
    if (newSort.includes(column)) {
      newSort = newSort.startsWith("-") ? "-created_at" : `-${column}`;
    } else {
      newSort = column;
    }
    onFilterChange({ sort: newSort });
  };

  return (
    <Box id="users-table" dir={direction} borderTopWidth="1px" borderColor="gray.200" _dark={{ borderColor: "#33483b" }} minW={0}>
      {users.length === 0 ? (
        <EmptySection isFiltered={isFiltered} />
      ) : (
        <>
          <Stack display={{ base: "flex", md: "none" }} spacing={3} py={4}>
            {users.map((user) => (
              <Card key={user.username} variant="outline" p={4} borderRadius="10px" borderColor="gray.200" _dark={{ borderColor: "#33483b" }} boxShadow="none">
                <Stack spacing={4}>
                  <HStack justify="space-between" align="start" gap={3}>
                    <Box minW={0}>
                      <HStack spacing={2} minW={0}>
                        <OnlineBadge lastOnline={user.online_at} />
                        <Text dir="ltr" textAlign="start" fontWeight="600" overflowWrap="anywhere" minW={0} sx={{ unicodeBidi: "isolate" }}>{user.username}</Text>
                      </HStack>
                      <OnlineStatus lastOnline={user.online_at} />
                    </Box>
                    <StatusBadge compact expiryDate={user.expire} status={user.status} />
                  </HStack>
                  <UsageMeter
                    used={user.used_traffic}
                    total={user.data_limit}
                    totalUsedTraffic={user.lifetime_used_traffic}
                    dataLimitResetStrategy={user.data_limit_reset_strategy}
                    colorScheme={statusColors[user.status].bandWidthColor}
                  />
                  <Box borderTopWidth="1px" borderColor="gray.200" _dark={{ borderColor: "#33483b" }} pt={2}>
                    <ActionButtons user={user} />
                  </Box>
                </Stack>
              </Card>
            ))}
          </Stack>

          <TableContainer dir={direction} display={{ base: "none", md: "block" }} overflowX="auto" py={4} sx={{ scrollbarGutter: "stable" }}>
            <Table size="sm" w="full" minW="820px" tableLayout="fixed" {...props}>
              <Thead>
                <Tr>
                  <Th scope="col" w="22%" whiteSpace="normal" aria-sort={filters.sort.includes("username") ? (filters.sort.startsWith("-") ? "descending" : "ascending") : "none"}>
                    <SortLabel label={t("username")} column="username" sort={filters.sort} onSort={handleSort} />
                  </Th>
                  <Th scope="col" w="26%" whiteSpace="normal">
                    <HStack gap={2} flexWrap="wrap">
                      <Text>{t("usersTable.status")}</Text>
                      <Text color="gray.400">/</Text>
                      <SortLabel label={t("usersTable.expiration")} column="expire" sort={filters.sort} onSort={handleSort} />
                    </HStack>
                  </Th>
                  <Th scope="col" w="32%" whiteSpace="normal" aria-sort={filters.sort.includes("used_traffic") ? (filters.sort.startsWith("-") ? "descending" : "ascending") : "none"}>
                    <SortLabel label={t("usersTable.dataUsage")} column="used_traffic" sort={filters.sort} onSort={handleSort} />
                  </Th>
                  <Th scope="col" w="20%" whiteSpace="normal" textAlign="end">{t("admins.actions")}</Th>
                </Tr>
              </Thead>
              <Tbody>
                {users.map((user, index) => (
                  <Tr
                    key={user.username}
                    className={classNames("interactive", { "last-row": index === users.length - 1 })}
                    onClick={() => onEditingUser(user)}
                  >
                    <Td>
                      <HStack align="start" spacing={2} minW={0}>
                        <OnlineBadge lastOnline={user.online_at} />
                        <Box minW={0}>
                          <Text dir="ltr" textAlign="start" fontWeight="600" overflowWrap="anywhere" sx={{ unicodeBidi: "isolate" }}>{user.username}</Text>
                          <OnlineStatus lastOnline={user.online_at} />
                        </Box>
                      </HStack>
                    </Td>
                    <Td><StatusBadge expiryDate={user.expire} status={user.status} /></Td>
                    <Td>
                      <UsageMeter
                        used={user.used_traffic}
                        total={user.data_limit}
                        totalUsedTraffic={user.lifetime_used_traffic}
                        dataLimitResetStrategy={user.data_limit_reset_strategy}
                        colorScheme={statusColors[user.status].bandWidthColor}
                      />
                    </Td>
                    <Td><ActionButtons user={user} /></Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </TableContainer>
        </>
      )}
      <Pagination />
    </Box>
  );
};
