# Design patterns

The pattern library of agk design standard 1 (SPEC-0037 rule 1). Each pattern has its `default` state and the six
required states `empty`, `loading`, `error`, `no-permission`, `long-content` and `success`, each one block of markup
that uses only the classes of `design-standard.css`: no `style` attribute, and no colour, size or font of its own. Status
is always a word as well as a colour. Fixture slots are written in double braces, such as `{{person.name}}`, and are
filled from the kit's invented fixture set by the prototype writer; a page never holds real data.

## app shell and navigation

### default

```html
<div class="shell">
  <header class="shell-header">
    <span class="brand">{{product.name}}</span>
    <a class="button" href="{{link.account}}">{{person.name}}</a>
  </header>
  <nav class="shell-nav" aria-label="Main">
    <ul class="nav-list">
      <li><a class="nav-link" href="{{link.home}}" aria-current="page">Home</a></li>
      <li><a class="nav-link" href="{{link.list}}">Items</a></li>
      <li><a class="nav-link" href="{{link.settings}}">Settings</a></li>
    </ul>
  </nav>
  <main class="shell-main" id="main">
    <h1>{{page.title}}</h1>
  </main>
</div>
```

### empty

```html
<div class="shell">
  <header class="shell-header"><span class="brand">{{product.name}}</span></header>
  <nav class="shell-nav" aria-label="Main">
    <ul class="nav-list">
      <li><a class="nav-link" href="{{link.home}}" aria-current="page">Home</a></li>
    </ul>
  </nav>
  <main class="shell-main" id="main">
    <h1>{{page.title}}</h1>
    <div class="empty"><p>Nothing here yet.</p></div>
  </main>
</div>
```

### loading

```html
<div class="shell">
  <header class="shell-header"><span class="brand">{{product.name}}</span></header>
  <main class="shell-main" id="main" aria-busy="true">
    <h1>{{page.title}}</h1>
    <p class="muted" role="status">Loading…</p>
    <div class="skeleton"></div>
  </main>
</div>
```

### error

```html
<div class="shell">
  <header class="shell-header"><span class="brand">{{product.name}}</span></header>
  <main class="shell-main" id="main">
    <h1>{{page.title}}</h1>
    <div class="alert alert-danger" role="alert"><p><strong>Error.</strong> The page could not be loaded.</p></div>
  </main>
</div>
```

### no-permission

```html
<div class="shell">
  <header class="shell-header"><span class="brand">{{product.name}}</span></header>
  <main class="shell-main" id="main">
    <h1>{{page.title}}</h1>
    <div class="alert alert-info" role="status"><p><strong>No access.</strong> Ask {{person.admin_name}} for access.</p></div>
  </main>
</div>
```

### long-content

```html
<div class="shell">
  <header class="shell-header">
    <span class="brand long-text">{{product.long_name}}</span>
    <a class="button long-text" href="{{link.account}}">{{person.long_name}}</a>
  </header>
  <nav class="shell-nav" aria-label="Main">
    <ul class="nav-list">
      <li><a class="nav-link long-text" href="{{link.home}}" aria-current="page">{{text.long_label}}</a></li>
    </ul>
  </nav>
  <main class="shell-main" id="main"><h1 class="long-text">{{text.long_title}}</h1></main>
</div>
```

### success

```html
<div class="shell">
  <header class="shell-header"><span class="brand">{{product.name}}</span></header>
  <main class="shell-main" id="main">
    <h1>{{page.title}}</h1>
    <div class="alert alert-success" role="status"><p><strong>Saved.</strong> Your changes are saved.</p></div>
  </main>
</div>
```

## list with filter and sort

### default

```html
<section class="stack">
  <h1>Items</h1>
  <form class="toolbar" role="search">
    <div class="field"><label for="filter">Filter</label><input class="input" id="filter" name="filter" type="search"></div>
    <div class="field"><label for="sort">Sort by</label>
      <select class="input" id="sort" name="sort"><option>Newest</option><option>Name</option></select></div>
    <button type="submit" class="button">Apply</button>
  </form>
  <ul class="list">
    <li class="list-item"><a href="{{link.item}}">{{item.title}}</a> <span class="muted">{{item.date}}</span></li>
    <li class="list-item"><a href="{{link.item}}">{{item.title_2}}</a> <span class="muted">{{item.date_2}}</span></li>
  </ul>
</section>
```

### empty

```html
<div class="empty">
  <h2>No items yet</h2>
  <p>Add the first item, or clear the filter.</p>
  <a class="button button-primary" href="{{link.create}}">Add an item</a>
</div>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading items…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The items could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these items. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<ul class="list">
  <li class="list-item long-text"><a href="{{link.item}}">{{text.long_title}}</a> <span class="muted">{{item.date}}</span></li>
  <li class="list-item long-text">{{text.long_paragraph}}</li>
</ul>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The item was added to the list.</p>
</div>
```

## detail

### default

```html
<article class="stack">
  <h1>{{item.title}}</h1>
  <dl class="detail-list">
    <dt>Owner</dt><dd>{{person.name}}</dd>
    <dt>Organisation</dt><dd>{{organisation.name}}</dd>
    <dt>Amount</dt><dd>{{amount.value}}</dd>
    <dt>Updated</dt><dd>{{item.date}}</dd>
  </dl>
  <div class="cluster"><a class="button button-primary" href="{{link.edit}}">Edit</a></div>
</article>
```

### empty

```html
<article class="stack">
  <h1>{{item.title}}</h1>
  <p class="empty">This item has no details yet.</p>
</article>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading the item…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The item could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see this item. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<article class="stack">
  <h1 class="long-text">{{text.long_title}}</h1>
  <dl class="detail-list">
    <dt>Owner</dt><dd class="long-text">{{person.long_name}}</dd>
    <dt>Address</dt><dd class="long-text">{{address.long}}</dd>
  </dl>
</article>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The item was updated.</p>
</div>
```

## form with validation

### default

```html
<form class="stack" novalidate>
  <h1>New item</h1>
  <div class="field">
    <label for="name">Name</label>
    <input class="input" id="name" name="name" autocomplete="name" aria-describedby="name-hint">
    <p class="hint" id="name-hint">As it should appear on the record.</p>
  </div>
  <div class="field">
    <label for="email">Email</label>
    <input class="input" id="email" name="email" type="email" autocomplete="email">
  </div>
  <div class="cluster"><button type="submit" class="button button-primary">Save</button></div>
</form>
```

### empty

```html
<form class="stack" novalidate>
  <h1>New item</h1>
  <p class="muted">Every field is empty; required fields are marked.</p>
  <div class="field">
    <label for="name">Name (required)</label>
    <input class="input" id="name" name="name" required>
  </div>
  <div class="cluster"><button type="submit" class="button button-primary">Save</button></div>
</form>
```

### loading

```html
<form class="stack" aria-busy="true">
  <h1>New item</h1>
  <p class="muted" role="status">Saving…</p>
  <div class="cluster"><button type="submit" class="button button-primary" disabled>Save</button></div>
</form>
```

### error

```html
<form class="stack" novalidate>
  <h1>New item</h1>
  <div class="alert alert-danger" role="alert"><p><strong>Error.</strong> One field needs a change.</p></div>
  <div class="field">
    <label for="email">Email</label>
    <input class="input" id="email" name="email" type="email" aria-invalid="true" aria-describedby="email-error">
    <p class="field-error" id="email-error">Enter an email address such as {{person.email}}.</p>
  </div>
  <div class="cluster"><button type="submit" class="button button-primary">Save</button></div>
</form>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see this form. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<form class="stack" novalidate>
  <h1 class="long-text">{{text.long_title}}</h1>
  <div class="field">
    <label for="note" class="long-text">{{text.long_label}}</label>
    <textarea class="input long-text" id="note" name="note">{{text.long_paragraph}}</textarea>
  </div>
</form>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The form was saved.</p>
</div>
```

## table

### default

```html
<section class="stack">
  <h1>Payments</h1>
  <div class="table-wrap">
    <table class="table">
      <caption class="muted">Payments this month</caption>
      <thead><tr><th scope="col">Date</th><th scope="col">Organisation</th><th scope="col">Amount</th></tr></thead>
      <tbody>
        <tr><td>{{item.date}}</td><td>{{organisation.name}}</td><td>{{amount.value}}</td></tr>
        <tr><td>{{item.date_2}}</td><td>{{organisation.name_2}}</td><td>{{amount.value_2}}</td></tr>
      </tbody>
    </table>
  </div>
</section>
```

### empty

```html
<div class="empty">
  <h2>No payments yet</h2>
  <p>Payments appear here once one is recorded.</p>
  <a class="button button-primary" href="{{link.create}}">Record a payment</a>
</div>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading payments…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The payments could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these payments. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<div class="table-wrap">
  <table class="table">
    <thead><tr><th scope="col">Organisation</th><th scope="col">Address</th></tr></thead>
    <tbody><tr><td class="long-text">{{organisation.long_name}}</td><td class="long-text">{{address.long}}</td></tr></tbody>
  </table>
</div>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The payment was recorded.</p>
</div>
```

## dashboard

### default

```html
<section class="stack">
  <h1>Overview</h1>
  <div class="grid">
    <div class="card"><h2>Open items</h2><p class="metric-value">{{metric.open}}</p></div>
    <div class="card"><h2>Paid this month</h2><p class="metric-value">{{amount.total}}</p></div>
    <div class="card"><h2>Overdue</h2><p class="metric-value">{{metric.overdue}}</p> <span class="badge">Needs action</span></div>
  </div>
</section>
```

### empty

```html
<div class="empty">
  <h2>No figures yet</h2>
  <p>Figures appear once there is data to count.</p>
  <a class="button button-primary" href="{{link.create}}">Add data</a>
</div>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading the figures…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The figures could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these figures. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<div class="grid">
  <div class="card long-text"><h2>{{text.long_label}}</h2><p class="metric-value">{{metric.long}}</p></div>
</div>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The figures are up to date.</p>
</div>
```

## wizard

### default

```html
<section class="stack">
  <h1>Set up</h1>
  <ol class="steps" aria-label="Progress">
    <li class="step" aria-current="step">1. Details</li>
    <li class="step">2. Address</li>
    <li class="step">3. Review</li>
  </ol>
  <form class="stack">
    <div class="field"><label for="org">Organisation</label><input class="input" id="org" name="org"></div>
    <div class="cluster">
      <a class="button" href="{{link.back}}">Back</a>
      <button type="submit" class="button button-primary">Next</button>
    </div>
  </form>
</section>
```

### empty

```html
<section class="stack">
  <h1>Set up</h1>
  <p class="empty">Nothing is filled in yet. Start with step 1.</p>
  <a class="button button-primary" href="{{link.start}}">Start</a>
</section>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading the next step…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<section class="stack">
  <h1>Set up</h1>
  <div class="alert alert-danger" role="alert"><p><strong>Error.</strong> This step could not be saved.</p></div>
  <a class="button" href="{{link.back}}">Back</a>
</section>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see this set-up. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<ol class="steps" aria-label="Progress">
  <li class="step long-text" aria-current="step">{{text.long_label}}</li>
  <li class="step long-text">{{text.long_label_2}}</li>
</ol>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> Set-up is complete.</p>
</div>
```

## search

### default

```html
<section class="stack">
  <h1>Search</h1>
  <form class="toolbar" role="search">
    <div class="field"><label for="q">Search for</label><input class="input" id="q" name="q" type="search"></div>
    <button type="submit" class="button button-primary">Search</button>
  </form>
  <p class="muted" role="status">2 results</p>
  <ul class="list">
    <li class="list-item"><a href="{{link.item}}">{{item.title}}</a></li>
    <li class="list-item"><a href="{{link.item}}">{{item.title_2}}</a></li>
  </ul>
</section>
```

### empty

```html
<div class="empty">
  <h2>No results</h2>
  <p>Try fewer words, or check the spelling.</p>
</div>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading results…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The results could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these results. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<ul class="list">
  <li class="list-item long-text"><a href="{{link.item}}">{{text.long_title}}</a><p class="muted">{{text.long_paragraph}}</p></li>
</ul>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> The search was saved.</p>
</div>
```

## settings

### default

```html
<form class="stack">
  <h1>Settings</h1>
  <fieldset class="card stack">
    <legend>Notifications</legend>
    <div class="cluster"><input id="mail" name="mail" type="checkbox" checked><label for="mail">Email me a summary</label></div>
  </fieldset>
  <fieldset class="card stack">
    <legend>Profile</legend>
    <div class="field"><label for="display">Display name</label><input class="input" id="display" name="display"></div>
  </fieldset>
  <div class="cluster"><button type="submit" class="button button-primary">Save settings</button></div>
</form>
```

### empty

```html
<section class="stack">
  <h1>Settings</h1>
  <p class="empty">There are no settings to change yet.</p>
</section>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading settings…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The settings could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these settings. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<fieldset class="card stack">
  <legend class="long-text">{{text.long_label}}</legend>
  <p class="hint long-text">{{text.long_paragraph}}</p>
</fieldset>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> Your settings are saved.</p>
</div>
```

## notifications

### default

```html
<section class="stack">
  <h1>Notifications</h1>
  <ul class="list">
    <li class="list-item" data-unread="true"><strong>New</strong> {{notice.text}} <span class="muted">{{item.date}}</span></li>
    <li class="list-item">{{notice.text_2}} <span class="muted">{{item.date_2}}</span></li>
  </ul>
  <div class="cluster"><button type="button" class="button">Mark all as read</button></div>
</section>
```

### empty

```html
<div class="empty">
  <h2>No notifications yet</h2>
  <p>You are up to date.</p>
  <a class="button button-primary" href="{{link.create}}">Open settings</a>
</div>
```

### loading

```html
<div class="stack" aria-busy="true">
  <p class="muted" role="status">Loading notifications…</p>
  <div class="skeleton"></div>
  <div class="skeleton"></div>
</div>
```

### error

```html
<div class="alert alert-danger" role="alert">
  <p><strong>Error.</strong> The notifications could not be loaded.</p>
  <button type="button" class="button">Try again</button>
</div>
```

### no-permission

```html
<div class="alert alert-info" role="status">
  <p><strong>No access.</strong> You do not have permission to see these notifications. Ask {{person.admin_name}} for access.</p>
</div>
```

### long-content

```html
<ul class="list">
  <li class="list-item long-text" data-unread="true"><strong>New</strong> {{text.long_paragraph}}</li>
</ul>
```

### success

```html
<div class="alert alert-success" role="status">
  <p><strong>Done.</strong> All notifications are marked as read.</p>
</div>
```

## confirmation dialog

### default

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title">Delete this item?</h2>
  <p>{{item.title}} will be removed. This cannot be undone.</p>
  <div class="dialog-actions">
    <button type="button" class="button">Cancel</button>
    <button type="button" class="button button-danger">Delete</button>
  </div>
</dialog>
```

### empty

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title">Nothing to delete</h2>
  <p>No item is selected.</p>
  <div class="dialog-actions"><button type="button" class="button">Close</button></div>
</dialog>
```

### loading

```html
<dialog class="dialog" open aria-labelledby="confirm-title" aria-busy="true">
  <h2 id="confirm-title">Deleting…</h2>
  <p class="muted" role="status">Deleting {{item.title}}.</p>
</dialog>
```

### error

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title">Not deleted</h2>
  <div class="alert alert-danger" role="alert"><p><strong>Error.</strong> The item could not be deleted.</p></div>
  <div class="dialog-actions"><button type="button" class="button">Close</button></div>
</dialog>
```

### no-permission

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title">No access</h2>
  <p>You do not have permission to delete this item. Ask {{person.admin_name}}.</p>
  <div class="dialog-actions"><button type="button" class="button">Close</button></div>
</dialog>
```

### long-content

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title" class="long-text">{{text.long_title}}</h2>
  <p class="long-text">{{text.long_paragraph}}</p>
  <div class="dialog-actions"><button type="button" class="button">Cancel</button></div>
</dialog>
```

### success

```html
<dialog class="dialog" open aria-labelledby="confirm-title">
  <h2 id="confirm-title">Deleted</h2>
  <div class="alert alert-success" role="status"><p><strong>Done.</strong> The item was deleted.</p></div>
  <div class="dialog-actions"><button type="button" class="button">Close</button></div>
</dialog>
```
