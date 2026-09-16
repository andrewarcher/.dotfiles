-- nvim 0.11+. No plugin manager: LSP and completion are nvim built-ins, and
-- the one plugin (nvim-lspconfig, for its maintained server definitions) is a
-- git submodule loaded via native packpath.
--
-- Settings that nvim already defaults to (nocompatible, syntax, filetype
-- plugin indent, incsearch, hlsearch, autoread, autoindent, nobackup, utf-8)
-- are deliberately absent -- only real preferences live here.

--
-- state
--

vim.o.shada = "%,<800,'10,/50,:100,h,f0"
--            | |    |   |   |    | + file marks 0-9,A-Z 0=NOT stored
--            | |    |   |   |    + disable 'hlsearch' loading shada
--            | |    |   |   + command-line history saved
--            | |    |   + search history saved
--            | |    + files marks saved
--            | + lines saved each register
--            + save/restore buffer list
-- NOTE: no `n<path>` -- nvim keeps shada under stdpath("state") itself.

--
-- file management
--

vim.o.autowrite = true -- automatically save before :next, :make, ..etc
vim.o.swapfile = false -- don't use swapfile

--
-- search
--

vim.o.ignorecase = true -- search case insensitive...
vim.o.smartcase = true  -- ...but not if it begins with an upper case

--
-- interface
--

vim.o.number = true       -- show line numbers
vim.o.signcolumn = "yes"  -- always show left bar for diagnostics etc
vim.cmd.colorscheme("toast")

--
-- shortcuts
--

vim.keymap.set("i", "kj", "<Esc>")
vim.keymap.set("", "<ScrollWheelDown>", "k")
vim.keymap.set("", "<ScrollWheelUp>", "j")

--
-- file formatting
--

vim.o.tabstop = 4    -- tabs are 4 spaces wide
vim.o.shiftwidth = 0 -- '<' and '>' shifts de/indent by tabstop distance
vim.o.expandtab = true -- convert tabs to spaces

--
-- server binary resolution
--
-- The Brewfile installs a default of every server, but a project pinning its
-- own toolchain has to win. Resolved per project root, in order:
--
--   1. project-local bin -- node_modules/.bin, .venv/bin
--   2. mise, asked for the version active in THAT directory
--   3. Homebrew -- the Brewfile default
--   4. PATH
--
-- Step 2 is why PATH alone will not do: mise shims sit on PATH globally and
-- are executable even with no version set, then exit 1 the moment they spawn
-- (`No version is set for shim: gopls`). Asking mise directly either yields a
-- real absolute path for this directory or fails cleanly into the Homebrew
-- default -- which is also why Homebrew is tried before bare PATH.

local brew = vim.env.HOMEBREW_PREFIX or "/opt/homebrew"
local resolved = {}

local function resolve(bin, root)
  root = root or vim.fn.getcwd()
  local key = bin .. "\0" .. root
  if resolved[key] then
    return resolved[key]
  end

  local found
  for _, dir in ipairs({ "/node_modules/.bin/", "/.venv/bin/" }) do
    local candidate = root .. dir .. bin
    if vim.uv.fs_stat(candidate) then
      found = candidate
      break
    end
  end

  if not found and vim.fn.executable("mise") == 1 then
    local r = vim.system({ "mise", "which", bin }, { cwd = root, text = true }):wait(5000)
    if r.code == 0 and vim.trim(r.stdout) ~= "" then
      found = vim.trim(r.stdout)
    end
  end

  if not found and vim.uv.fs_stat(brew .. "/bin/" .. bin) then
    found = brew .. "/bin/" .. bin
  end

  found = found or bin
  resolved[key] = found
  return found
end

-- Build a `cmd` callback so resolution happens per project root rather than
-- once at startup -- editing two repos on different toolchains in one nvim
-- session gets the right server for each.
local function cmd_for(bin, args)
  return function(dispatchers, config)
    local cmd = { resolve(bin, config.root_dir) }
    vim.list_extend(cmd, args or {})
    return vim.lsp.rpc.start(cmd, dispatchers)
  end
end

--
-- LSP
--
-- Server definitions come from the nvim-lspconfig submodule under
-- pack/plugins/start, which ships one maintained lsp/<name>.lua per server and
-- is picked up via nvim's packpath. Servers start lazily when a matching
-- buffer opens, so listing one you have not installed costs nothing.
--
-- Add a language: put its server in the Brewfile, then add a row here using
-- its nvim-lspconfig name. Everything not overridden tracks upstream.

local servers = {
  -- lspconfig name   binary                          args            overrides
  { "gopls",          "gopls",                        nil, {
      settings = { gopls = { analyses = { unusedparams = true }, staticcheck = true } },
    } },
  { "ts_ls",          "typescript-language-server",   { "--stdio" } },
  { "basedpyright",   "basedpyright-langserver",      { "--stdio" } },
  -- python is split: basedpyright owns types, ruff owns lint + format. Drop
  -- ruff's hover so the two do not both answer K in the same buffer.
  { "ruff",           "ruff",                         { "server" }, {
      on_attach = function(client)
        client.server_capabilities.hoverProvider = false
      end,
    } },
}

local names = {}
for _, s in ipairs(servers) do
  local name, bin, args, overrides = s[1], s[2], s[3], s[4] or {}
  overrides.cmd = cmd_for(bin, args)
  vim.lsp.config(name, overrides)
  names[#names + 1] = name
end
vim.lsp.enable(names)

-- :LspWhich -- print the binary each server resolves to for this buffer's
-- project root. The resolution order above is otherwise invisible, and "which
-- gopls am I actually running" is the first question when one misbehaves.
vim.api.nvim_create_user_command("LspWhich", function()
  local root = vim.fs.root(0, { ".git", "go.mod", "package.json", "pyproject.toml", "mise.toml" })
    or vim.fn.getcwd()
  local lines = { "root: " .. root }
  for _, s in ipairs(servers) do
    lines[#lines + 1] = ("  %-14s %s"):format(s[1], resolve(s[2], root))
  end
  vim.notify(table.concat(lines, "\n"))
end, { desc = "Show resolved LSP server binaries for this project" })

vim.diagnostic.config({
  virtual_text = true,
  severity_sort = true,
})

vim.api.nvim_create_autocmd("LspAttach", {
  callback = function(args)
    local client = vim.lsp.get_client_by_id(args.data.client_id)
    if not client then
      return
    end

    -- as-you-type completion, built in -- no nvim-cmp/blink needed
    if client:supports_method("textDocument/completion") then
      vim.lsp.completion.enable(true, client.id, args.buf, { autotrigger = true })
    end

    -- nvim maps grn/gra/grr/gri and K by default; these are the vim-go muscle
    -- memory (gd -> definition, K -> hover) carried over.
    local function map(lhs, rhs)
      vim.keymap.set("n", lhs, rhs, { buffer = args.buf, silent = true })
    end
    map("gd", vim.lsp.buf.definition)
    map("gy", vim.lsp.buf.type_definition)
    map("<leader>rn", vim.lsp.buf.rename)

    -- format on save, where the server can do it
    if client:supports_method("textDocument/formatting") then
      vim.api.nvim_create_autocmd("BufWritePre", {
        buffer = args.buf,
        callback = function()
          vim.lsp.buf.format({ bufnr = args.buf, id = client.id })
        end,
      })
    end
  end,
})
