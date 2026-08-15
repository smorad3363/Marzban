import {
  Badge,
  Box,
  BoxProps,
  Button,
  Card,
  chakra,
  CircularProgress,
  CircularProgressLabel,
  Collapse,
  Divider,
  HStack,
  IconButton,
  Popover,
  PopoverArrow,
  PopoverBody,
  PopoverCloseButton,
  PopoverContent,
  PopoverHeader,
  PopoverTrigger,
  Portal,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
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
import { resetStrategy, statusColors } from "constants/UserSettings";
import { useDashboard } from "contexts/DashboardContext";
import { FC, ReactNode, useEffect, useState } from "react";
import CopyToClipboard from "react-copy-to-clipboard";
import { useTranslation } from "react-i18next";
import { User } from "types/User";
import { formatBytes } from "utils/formatByte";
import { OnlineBadge } from "./OnlineBadge";
import { Pagination } from "./Pagination";
import { StatusBadge } from "./StatusBadge";

const EmptySectionIcon = chakra(AddFileIcon);
const iconProps = { baseStyle: { w: 4, h: 4 } };
const CopyIcon = chakra(ClipboardIcon, iconProps);
const CopiedIcon = chakra(CheckIcon, iconProps);
const SubscriptionLinkIcon = chakra(LinkIcon, iconProps);
const QRIcon = chakra(QrCodeIcon, iconProps);
const EditIcon = chakra(PencilIcon, iconProps);
const DetailsIcon = chakra(ChevronDownIcon, { baseStyle: { w: 4, h: 4 } });

type UsageMeterProps = {
  used: number;
  total: number | null;
  dataLimitResetStrategy: string | null;
  totalUsedTraffic: number;
  colorScheme?: string;
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
}) => {
  const { t, i18n } = useTranslation();
  const direction = i18n.dir();
  const isUnlimited = total === 0 || total === null;
  const percent = isUnlimited ? 100 : Math.min((used / Math.max(total, 1)) * 100, 100);
  const isReached = !isUnlimited && percent >= 100;
  const ringColor = isReached
    ? "red.400"
    : colorScheme === "primary"
      ? "gold.400"
      : `${colorScheme}.400`;
  const limitText = isUnlimited
    ? "∞"
    : formatBytes(total) +
      (dataLimitResetStrategy && dataLimitResetStrategy !== "no_reset"
        ? ` ${t(`userDialog.resetStrategy${getResetStrategy(dataLimitResetStrategy)}`)}`
        : "");

  return (
    <HStack spacing={3} minW={0} dir={direction}>
      <CircularProgress
        value={percent}
        size="58px"
        thickness="8px"
        color={ringColor}
        trackColor="whiteAlpha.100"
        opacity={isUnlimited ? 0.78 : 1}
        aria-label={`${formatBytes(used)} / ${limitText}`}
        flexShrink={0}
      >
        <CircularProgressLabel
          dir="ltr"
          fontFamily="mono"
          fontSize="xs"
          fontWeight="700"
          color={isReached ? "red.300" : "gold.200"}
        >
          {isUnlimited ? "∞" : `${Math.round(percent)}%`}
        </CircularProgressLabel>
      </CircularProgress>
      <Stack spacing={0.5} minW={0}>
        <MetaLabel>{t("usersTable.dataUsage")}</MetaLabel>
        <Text dir="ltr" textAlign="start" fontSize="sm" fontFamily="mono" noOfLines={1} sx={{ unicodeBidi: "isolate" }}>
          {formatBytes(used)} / {limitText}
        </Text>
        <Text color="gray.400" fontSize="xs" noOfLines={1}>
          {t("usersTable.total")}: <Text as="span" dir="ltr" display="inline-block" fontFamily="mono" sx={{ unicodeBidi: "isolate" }}>{formatBytes(totalUsedTraffic)}</Text>
        </Text>
      </Stack>
    </HStack>
  );
};

const formatDateTime = (value: string | null | undefined, locale: string) => {
  if (!value) return "—";
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
};

const formatTimestamp = (value: number | null | undefined, locale: string) => {
  if (!value) return "—";
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
    new Date(value * 1000)
  );
};

const MetaLabel: FC<{ children: ReactNode }> = ({ children }) => (
  <Text color="gray.400" fontSize="xs" fontWeight="600" lineHeight="1.6">
    {children}
  </Text>
);

const NextPlanSummary: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const plan = user.next_plan;
  if (!plan) {
    return <Text color="gray.500" fontSize="sm">{t("usersTable.noNextPlan")}</Text>;
  }

  const limit = !plan.data_limit
    ? t("unlimited")
    : formatBytes(plan.data_limit);

  return (
    <Stack spacing={1.5} minW={0}>
      <HStack spacing={2} flexWrap="wrap">
        <Badge colorScheme="gold" variant="subtle" textTransform="none" fontFamily="mono">
          {limit}
        </Badge>
        <Text fontSize="xs" color="gray.300" dir="ltr" sx={{ unicodeBidi: "isolate" }}>
          {formatTimestamp(plan.expire, i18n.language)}
        </Text>
      </HStack>
      <Text fontSize="xs" color="gray.400" lineHeight="1.6">
        {plan.add_remaining_traffic
          ? t("usersTable.keepRemainingTraffic")
          : t("usersTable.replaceRemainingTraffic")}
        {" · "}
        {plan.fire_on_either
          ? t("usersTable.activateOnEither")
          : t("usersTable.activateOnBoth")}
      </Text>
    </Stack>
  );
};

const ResetHistory: FC<{ user: User }> = ({ user }) => {
  const { t, i18n } = useTranslation();
  const history = [...(user.reset_history || [])].sort(
    (a, b) => new Date(b.reset_at).getTime() - new Date(a.reset_at).getTime()
  );

  if (history.length === 0) {
    return <Text color="gray.500" fontSize="xs">{t("usersTable.noResetHistory")}</Text>;
  }

  return (
    <Popover isLazy placement="auto" strategy="fixed">
      <PopoverTrigger>
        <Button
          variant="link"
          colorScheme="gold"
          size="sm"
          minH="36px"
          fontSize="xs"
          onClick={(event) => event.stopPropagation()}
        >
          {t("usersTable.resetCount", { count: history.length })}
        </Button>
      </PopoverTrigger>
      <Portal>
        <PopoverContent
          dir={i18n.dir()}
          bg="#111d17"
          color="gray.100"
          borderColor="#475f50"
          maxW={{ base: "calc(100vw - 24px)", sm: "360px" }}
          onClick={(event) => event.stopPropagation()}
        >
          <PopoverArrow bg="#111d17" />
          <PopoverCloseButton />
          <PopoverHeader fontWeight="700" borderColor="#33483b" pe={10}>
            {t("usersTable.resetHistory")}
          </PopoverHeader>
          <PopoverBody maxH="280px" overflowY="auto" p={0}>
            {history.map((item, index) => (
              <Box key={`${item.reset_at}-${index}`} px={4} py={3}>
                <HStack justify="space-between" align="start" gap={4}>
                  <Text fontSize="sm" fontFamily="mono" dir="ltr" sx={{ unicodeBidi: "isolate" }}>
                    {formatBytes(item.used_traffic)}
                  </Text>
                  <Text fontSize="xs" color="gray.400" textAlign="end">
                    {formatDateTime(item.reset_at, i18n.language)}
                  </Text>
                </HStack>
                {index < history.length - 1 && <Divider mt={3} borderColor="#33483b" />}
              </Box>
            ))}
          </PopoverBody>
        </PopoverContent>
      </Portal>
    </Popover>
  );
};

type ActionButtonsProps = { user: User };

const ActionButtons: FC<ActionButtonsProps> = ({ user }) => {
  const { setQRCode, setSubLink } = useDashboard();
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
    minW: "44px",
    h: "44px",
    color: "gray.300",
    _hover: { bg: "gold.900", color: "gold.200" },
    _focusVisible: { boxShadow: "0 0 0 2px var(--chakra-colors-gold-400)" },
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
    </HStack>
  );
};

type UserCardProps = {
  user: User;
  expanded: boolean;
  onToggle: () => void;
  onOpen: () => void;
};

const UserCard: FC<UserCardProps> = ({ user, expanded, onToggle, onOpen }) => {
  const { t, i18n } = useTranslation();
  const owner = user.admin?.username || "—";

  return (
    <Card
      as="article"
      variant="outline"
      minW={0}
      maxW="full"
      overflow="hidden"
      position="relative"
      borderRadius="14px"
      borderColor={expanded ? "gold.700" : "#33483b"}
      boxShadow={expanded ? "0 14px 36px rgba(0, 0, 0, 0.28)" : "none"}
      transition="border-color 180ms ease, box-shadow 180ms ease"
      _hover={{ borderColor: "gold.600", boxShadow: "0 12px 30px rgba(0, 0, 0, 0.24)" }}
    >
      <Box
        aria-hidden="true"
        position="absolute"
        top={0}
        insetInline={0}
        h="2px"
        bgGradient="linear(to-r, transparent, gold.400, transparent)"
        opacity={expanded ? 1 : 0.58}
      />

      <Box
        as="button"
        type="button"
        w="full"
        minW={0}
        p={{ base: 3.5, md: 4 }}
        pt={{ base: 4, md: 4.5 }}
        textAlign="start"
        cursor="pointer"
        onClick={onOpen}
        aria-label={`${t("userDialog.editUser")}: ${user.username}`}
        _hover={{ bg: "whiteAlpha.50" }}
        _focusVisible={{ outline: "2px solid", outlineColor: "gold.400", outlineOffset: "-2px" }}
        transition="background-color 160ms ease"
      >
        <Stack spacing={3.5} minW={0}>
          <HStack justify="space-between" align="start" gap={3} minW={0}>
            <Box minW={0} flex="1">
              <HStack spacing={2} minW={0}>
                <OnlineBadge lastOnline={user.online_at} />
                <Text
                  dir="ltr"
                  textAlign="start"
                  fontFamily="mono"
                  fontSize="sm"
                  fontWeight="700"
                  noOfLines={1}
                  minW={0}
                  sx={{ unicodeBidi: "isolate" }}
                >
                  {user.username}
                </Text>
              </HStack>
              <Text mt={1.5} color="gray.400" fontSize="xs" noOfLines={1}>
                {t("usersTable.owner")}: <Text as="span" color="gold.200" dir="ltr" sx={{ unicodeBidi: "isolate" }}>{owner}</Text>
              </Text>
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
        </Stack>
      </Box>

      <HStack
        justify="space-between"
        align="center"
        gap={2}
        px={3}
        py={2}
        borderTopWidth="1px"
        borderColor="#33483b"
        bg="blackAlpha.100"
      >
        <ActionButtons user={user} />
        <HStack spacing={1} flexShrink={0}>
          <Tooltip label={t("userDialog.editUser")} placement="top">
            <IconButton
              aria-label={t("userDialog.editUser")}
              icon={<EditIcon />}
              variant="ghost"
              color="gold.200"
              minW="44px"
              h="44px"
              onClick={onOpen}
              _hover={{ bg: "gold.900" }}
            />
          </Tooltip>
          <Button
            variant="ghost"
            minH="44px"
            px={2.5}
            color="gray.300"
            fontSize="xs"
            rightIcon={
              <DetailsIcon
                aria-hidden="true"
                transform={expanded ? "rotate(180deg)" : undefined}
                transition="transform 180ms ease"
              />
            }
            aria-expanded={expanded}
            onClick={onToggle}
            _hover={{ bg: "gold.900", color: "gold.100" }}
          >
            {expanded ? t("usersTable.hideDetails") : t("usersTable.showDetails")}
          </Button>
        </HStack>
      </HStack>

      <Collapse in={expanded} animateOpacity>
        <Box px={4} py={4} borderTopWidth="1px" borderColor="gold.900" bg="blackAlpha.200">
          <SimpleGrid columns={{ base: 1, sm: 2 }} gap={4} minW={0}>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.owner")}</MetaLabel>
              <Text mt={1} fontSize="sm" dir="ltr" textAlign="start" overflowWrap="anywhere" sx={{ unicodeBidi: "isolate" }}>{owner}</Text>
            </Box>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.createdAt")}</MetaLabel>
              <Text mt={1} fontSize="sm" lineHeight="1.7">{formatDateTime(user.created_at, i18n.language)}</Text>
            </Box>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.subscriptionUpdatedAt")}</MetaLabel>
              <Text mt={1} fontSize="sm" lineHeight="1.7">{formatDateTime(user.sub_updated_at, i18n.language)}</Text>
            </Box>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.lastUserAgent")}</MetaLabel>
              <Text mt={1} fontSize="sm" dir="ltr" textAlign="start" overflowWrap="anywhere" sx={{ unicodeBidi: "isolate" }}>
                {user.sub_last_user_agent || "—"}
              </Text>
            </Box>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.nextPlan")}</MetaLabel>
              <Box mt={1}><NextPlanSummary user={user} /></Box>
            </Box>
            <Box minW={0}>
              <MetaLabel>{t("usersTable.resetHistory")}</MetaLabel>
              <ResetHistory user={user} />
            </Box>
          </SimpleGrid>
        </Box>
      </Collapse>
    </Card>
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

type UsersTableProps = BoxProps;

export const UsersTable: FC<UsersTableProps> = (props) => {
  const {
    filters,
    users: { users },
    onEditingUser,
  } = useDashboard();
  const { i18n } = useTranslation();
  const direction = i18n.dir();
  const isFiltered = Boolean(filters.search || filters.status);
  const [expandedUser, setExpandedUser] = useState<string | null>(null);

  return (
    <Box
      {...props}
      id="users-table"
      dir={direction}
      w="full"
      maxW="full"
      minW={0}
      overflowX="hidden"
      borderTopWidth="1px"
      borderColor="gray.200"
      _dark={{ borderColor: "#33483b" }}
    >
      {users.length === 0 ? (
        <EmptySection isFiltered={isFiltered} />
      ) : (
        <SimpleGrid
          columns={{ base: 1, md: 2, xl: 3 }}
          gap={{ base: 3, md: 4 }}
          w="full"
          maxW="full"
          minW={0}
          py={4}
          alignItems="start"
        >
          {users.map((user) => (
            <UserCard
              key={user.username}
              user={user}
              expanded={expandedUser === user.username}
              onToggle={() => setExpandedUser((current) => current === user.username ? null : user.username)}
              onOpen={() => onEditingUser(user)}
            />
          ))}
        </SimpleGrid>
      )}
      <Pagination />
    </Box>
  );
};
