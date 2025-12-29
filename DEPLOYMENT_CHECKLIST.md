# Deployment Checklist

Use this checklist to ensure everything is ready for deployment.

## Pre-Deployment

### Codebase
- [ ] All code changes committed
- [ ] Code pushed to GitHub
- [ ] `Procfile` exists and is correct
- [ ] `requirements.txt` includes `gunicorn`
- [ ] `railway.json` exists (optional)
- [ ] `.gitignore` excludes sensitive files

### Supabase
- [ ] Supabase account created
- [ ] Project created
- [ ] Database password saved securely
- [ ] Connection string copied
- [ ] Tables created (`extraction_cache`, `user_choices`)
- [ ] Tables verified in Supabase dashboard

### Railway
- [ ] Railway account created
- [ ] GitHub connected to Railway
- [ ] Project created in Railway
- [ ] Repository selected

## Deployment Configuration

### Environment Variables (Set in Railway)
- [ ] `DATABASE_URL` - Supabase connection string
- [ ] `SECRET_KEY` - Generated secret key
- [ ] `PORT=5000`
- [ ] `FLASK_ENV=production`

### Build Settings
- [ ] Build command: (empty - auto-detect)
- [ ] Start command: `python -m gunicorn src.app:app --bind 0.0.0.0:$PORT`

## Post-Deployment

### Verification
- [ ] Deployment successful (green checkmark)
- [ ] App URL obtained
- [ ] App loads in browser
- [ ] No errors in Railway logs

### Functionality Testing
- [ ] PDF upload works
- [ ] Extraction works
- [ ] Assessments appear
- [ ] Lecture sections display correctly
- [ ] Calendar generation works
- [ ] Download works

### Database Verification
- [ ] Supabase connection works
- [ ] Data appears in `extraction_cache` table
- [ ] Data appears in `user_choices` table

## Troubleshooting

If something fails:
- [ ] Check Railway logs
- [ ] Verify environment variables
- [ ] Check Supabase project status
- [ ] Verify database tables exist
- [ ] Test database connection

---

**Ready to deploy?** Follow `DEPLOYMENT_STEPS.md` for detailed instructions.

